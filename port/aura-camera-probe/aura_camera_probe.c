// SPDX-License-Identifier: GPL-2.0-only
/* One-shot identification only. No sensor configuration or streaming writes. */
#include <linux/clk.h>
#include <linux/delay.h>
#include <linux/gpio/consumer.h>
#include <linux/i2c.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/regulator/consumer.h>

struct probe_spec { u16 reg, id; unsigned int delay; };
static const struct probe_spec tele = { 0x0016, 0x0351, 11 };
static const struct probe_spec front = { 0x0000, 0x3087, 18 };
static unsigned int front_settle_ms = 18;
module_param(front_settle_ms, uint, 0400);
MODULE_PARM_DESC(front_settle_ms, "Front reset settling delay, 18..200 ms");

static int aura_probe(struct i2c_client *client)
{
    struct device *dev = &client->dev;
    const struct probe_spec *spec = device_get_match_data(dev);
    struct regulator_bulk_data *rails;
    struct gpio_desc *reset;
    struct clk *clock;
    u8 address[2], value[2];
    struct i2c_msg messages[2];
    unsigned int powered = 0;
    int ret, stop_ret;

    if (!spec) return -EINVAL;
    if (front_settle_ms < 18 || front_settle_ms > 200) return -EINVAL;
    /* devm_regulator_bulk_get retains this array until device cleanup. */
    rails = devm_kcalloc(dev, 3, sizeof(*rails), GFP_KERNEL);
    if (!rails) return -ENOMEM;
    rails[0].supply = "vana";
    rails[1].supply = "vdig";
    rails[2].supply = "vio";
    reset = devm_gpiod_get(dev, "reset", GPIOD_OUT_HIGH);
    if (IS_ERR(reset)) return dev_err_probe(dev, PTR_ERR(reset), "reset unavailable\n");
    clock = devm_clk_get(dev, "xvclk");
    if (IS_ERR(clock)) return dev_err_probe(dev, PTR_ERR(clock), "clock unavailable\n");
    ret = devm_regulator_bulk_get(dev, 3, rails);
    if (ret) return dev_err_probe(dev, ret, "supplies unavailable\n");
    ret = clk_set_rate(clock, 24000000);
    if (ret) return ret;
    if (clk_get_rate(clock) != 24000000) return -EINVAL;

    /* Same rail order as the retained module's VANA/VDIG/VIO sequence. */
    usleep_range(1000, 1500);
    for (powered = 0; powered < 3; ++powered) {
        ret = regulator_enable(rails[powered].consumer);
        if (ret) goto off;
        if (spec == &front) msleep(front_settle_ms > 18 ? 20 : 1);
    }
    ret = clk_prepare_enable(clock);
    if (ret) goto off;
    usleep_range(1000, 1500);
    gpiod_set_value_cansleep(reset, 0);
    msleep(spec == &front ? front_settle_ms : spec->delay);
    dev_info(dev, "identity test clock=%lu reset-logical=%d settle=%u ms\n",
             clk_get_rate(clock), gpiod_get_value_cansleep(reset),
             spec == &front ? front_settle_ms : spec->delay);

    address[0] = spec->reg >> 8;
    address[1] = spec->reg & 0xff;
    messages[0] = (struct i2c_msg){ .addr = client->addr, .len = 2, .buf = address };
    messages[1] = (struct i2c_msg){ .addr = client->addr, .flags = I2C_M_RD, .len = 2, .buf = value };
    ret = i2c_transfer(client->adapter, messages, 2);
    if (ret == 2) {
        const u16 id = (value[0] << 8) | value[1];
        dev_info(dev, "camera identification: read 0x%04x expected 0x%04x\n", id, spec->id);
        ret = id == spec->id ? 0 : -ENODEV;
    } else {
        if (ret >= 0) ret = -EIO;
        dev_err(dev, "camera identification read failed: %d\n", ret);
    }
    gpiod_set_value_cansleep(reset, 1);
    usleep_range(1000, 1500);
    clk_disable_unprepare(clock);
off:
    while (powered) {
        stop_ret = regulator_disable(rails[--powered].consumer);
        if (stop_ret) dev_err(dev, "power-down failed: %d\n", stop_ret);
    }
    dev_info(dev, "one-shot camera probe finished; supplies released\n");
    return ret;
}

static const struct of_device_id matches[] = {
    { .compatible = "razer,aura-imx351-probe", .data = &tele },
    { .compatible = "razer,aura-s5k3h7-probe", .data = &front },
    { }
};
MODULE_DEVICE_TABLE(of, matches);
static struct i2c_driver aura_camera_probe_driver = {
    .driver = { .name = "aura-camera-probe", .of_match_table = matches },
    .probe = aura_probe,
};
module_i2c_driver(aura_camera_probe_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Read-only sensor identification using retained Razer power wiring");
