// SPDX-License-Identifier: GPL-2.0-only
/* Razer Phone 2 LM3644 torch-only bring-up. No flash/strobe mode exposed.
 * TI SNVSA52E: code 31 is <= 88.754 mA per LED, including the TT variant.
 */
#include <linux/delay.h>
#include <linux/gpio/consumer.h>
#include <linux/i2c.h>
#include <linux/leds.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/regmap.h>
#include <linux/regulator/consumer.h>

struct aura_torch {
	struct regmap *map;
	struct gpio_desc *enable;
	struct regulator *vdd;
	struct mutex lock;
	struct led_classdev led;
	bool powered;
};

static void aura_torch_off(struct aura_torch *torch)
{
	if (!torch->powered)
		return;
	regmap_write(torch->map, 0x01, 0x80);
	gpiod_set_value_cansleep(torch->enable, 0);
	regulator_disable(torch->vdd);
	torch->powered = false;
}

static int aura_torch_on(struct aura_torch *torch)
{
	unsigned int id;
	int ret;

	if (torch->powered)
		return 0;
	ret = regulator_enable(torch->vdd);
	if (ret)
		return ret;
	torch->powered = true;
	gpiod_set_value_cansleep(torch->enable, 1);
	usleep_range(1000, 2000);
	ret = regmap_read(torch->map, 0x0c, &id);
	if (ret)
		goto fail;
	if ((id & 0x07) != 0x02 && (id & 0x07) != 0x04) {
		ret = -ENODEV;
		goto fail;
	}
	/* Standby; retain TX safety input, disable external torch/strobe inputs. */
	ret = regmap_write(torch->map, 0x01, 0x80);
	if (!ret)
		return 0;
fail:
	aura_torch_off(torch);
	return ret;
}

static int aura_torch_set(struct led_classdev *led, enum led_brightness value)
{
	struct aura_torch *torch = container_of(led, struct aura_torch, led);
	int ret = 0;

	mutex_lock(&torch->lock);
	if (!value) {
		aura_torch_off(torch);
		goto out;
	}
	if (value > 32) {
		ret = -EINVAL;
		goto out;
	}
	ret = aura_torch_on(torch);
	if (ret)
		goto out;
	/* LED2 follows LED1. Codes 0..31; no flash-current registers touched. */
	ret = regmap_write(torch->map, 0x05, 0x80 | (value - 1));
	if (!ret)
		ret = regmap_write(torch->map, 0x01, 0x8b);
	if (ret)
		aura_torch_off(torch);
out:
	mutex_unlock(&torch->lock);
	return ret;
}

static void aura_torch_cleanup(void *data)
{
	struct aura_torch *torch = data;

	mutex_lock(&torch->lock);
	aura_torch_off(torch);
	mutex_unlock(&torch->lock);
}

static int aura_torch_probe(struct i2c_client *client)
{
	static const struct regmap_config config = {
		.reg_bits = 8, .val_bits = 8, .max_register = 0x0d,
	};
	struct aura_torch *torch;
	struct gpio_desc *pin;
	int ret;

	torch = devm_kzalloc(&client->dev, sizeof(*torch), GFP_KERNEL);
	if (!torch)
		return -ENOMEM;
	mutex_init(&torch->lock);
	i2c_set_clientdata(client, torch);
	torch->map = devm_regmap_init_i2c(client, &config);
	if (IS_ERR(torch->map))
		return PTR_ERR(torch->map);
	torch->vdd = devm_regulator_get(&client->dev, "vdd");
	if (IS_ERR(torch->vdd))
		return dev_err_probe(&client->dev, PTR_ERR(torch->vdd), "VDD unavailable\n");
	torch->enable = devm_gpiod_get(&client->dev, "enable", GPIOD_OUT_LOW);
	if (IS_ERR(torch->enable))
		return PTR_ERR(torch->enable);
	pin = devm_gpiod_get(&client->dev, "strobe", GPIOD_OUT_LOW);
	if (IS_ERR(pin))
		return PTR_ERR(pin);
	pin = devm_gpiod_get(&client->dev, "torch", GPIOD_OUT_LOW);
	if (IS_ERR(pin))
		return PTR_ERR(pin);
	ret = devm_add_action_or_reset(&client->dev, aura_torch_cleanup, torch);
	if (ret)
		return ret;
	ret = aura_torch_on(torch);
	if (ret)
		return dev_err_probe(&client->dev, ret, "LM3644 identification failed\n");
	aura_torch_off(torch);
	torch->led.name = "aura:white:torch";
	torch->led.max_brightness = 32;
	torch->led.brightness_set_blocking = aura_torch_set;
	torch->led.flags = LED_CORE_SUSPENDRESUME;
	return devm_led_classdev_register(&client->dev, &torch->led);
}

static void aura_torch_shutdown(struct i2c_client *client)
{
	aura_torch_cleanup(i2c_get_clientdata(client));
}

static const struct of_device_id aura_torch_match[] = {
	{ .compatible = "razer,aura-lm3644-torch" }, { }
};
MODULE_DEVICE_TABLE(of, aura_torch_match);

static struct i2c_driver aura_torch_driver = {
	.driver = { .name = "aura-lm3644-torch", .of_match_table = aura_torch_match },
	.probe = aura_torch_probe,
	.shutdown = aura_torch_shutdown,
};
module_i2c_driver(aura_torch_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Razer Phone 2 conservative LM3644 torch control");
