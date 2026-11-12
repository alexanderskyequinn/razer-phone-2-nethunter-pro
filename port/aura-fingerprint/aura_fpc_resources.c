// SPDX-License-Identifier: GPL-2.0-only
/* Razer Phone 2 fingerprint electrical resources. No secure-world/SPI access.
 * GPIOs and reset timings follow the retained FIH FPC1235 platform driver.
 * Binding and sysfs ABI are experimental; this is not an Android HAL shim.
 */
#include <linux/atomic.h>
#include <linux/delay.h>
#include <linux/gpio/consumer.h>
#include <linux/interrupt.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/platform_device.h>

struct aura_fpc {
	struct device *dev;
	struct gpio_desc *reset;
	struct gpio_desc *irq;
	struct mutex lock;
	atomic64_t events;
};

static ssize_t irq_show(struct device *dev, struct device_attribute *attr,
		       char *buf)
{
	struct aura_fpc *fpc = dev_get_drvdata(dev);
	int value = gpiod_get_value_cansleep(fpc->irq);

	return value < 0 ? value : sysfs_emit(buf, "%d\n", value);
}
static DEVICE_ATTR_RO(irq);

static ssize_t irq_count_show(struct device *dev, struct device_attribute *attr,
			     char *buf)
{
	struct aura_fpc *fpc = dev_get_drvdata(dev);

	return sysfs_emit(buf, "%lld\n", atomic64_read(&fpc->events));
}
static DEVICE_ATTR_RO(irq_count);

static ssize_t reset_store(struct device *dev, struct device_attribute *attr,
			   const char *buf, size_t count)
{
	struct aura_fpc *fpc = dev_get_drvdata(dev);
	int ret;

	if (!sysfs_streq(buf, "1"))
		return -EINVAL;

	mutex_lock(&fpc->lock);
	/* reset-gpios is active low; acquire direction only on explicit reset. */
	ret = gpiod_direction_output(fpc->reset, 0);
	if (!ret) {
		usleep_range(100, 200);
		gpiod_set_value_cansleep(fpc->reset, 1);
		usleep_range(5000, 5100);
		gpiod_set_value_cansleep(fpc->reset, 0);
		usleep_range(5000, 5100);
	}
	mutex_unlock(&fpc->lock);
	return ret ? ret : count;
}
static DEVICE_ATTR_WO(reset);

static struct attribute *aura_fpc_attrs[] = {
	&dev_attr_irq.attr,
	&dev_attr_irq_count.attr,
	&dev_attr_reset.attr,
	NULL,
};
static const struct attribute_group aura_fpc_group = {
	.attrs = aura_fpc_attrs,
};

static irqreturn_t aura_fpc_irq(int irq, void *data)
{
	struct aura_fpc *fpc = data;

	atomic64_inc(&fpc->events);
	sysfs_notify(&fpc->dev->kobj, NULL, "irq");
	sysfs_notify(&fpc->dev->kobj, NULL, "irq_count");
	return IRQ_HANDLED;
}

static int aura_fpc_probe(struct platform_device *pdev)
{
	struct device *dev = &pdev->dev;
	struct aura_fpc *fpc;
	int irq, ret;

	fpc = devm_kzalloc(dev, sizeof(*fpc), GFP_KERNEL);
	if (!fpc)
		return -ENOMEM;
	fpc->dev = dev;
	mutex_init(&fpc->lock);
	atomic64_set(&fpc->events, 0);
	platform_set_drvdata(pdev, fpc);
	/* No automatic reset: preserve the boot firmware's sensor state. */
	fpc->reset = devm_gpiod_get(dev, "reset", GPIOD_ASIS);
	if (IS_ERR(fpc->reset))
		return dev_err_probe(dev, PTR_ERR(fpc->reset), "reset GPIO\n");
	fpc->irq = devm_gpiod_get(dev, "irq", GPIOD_IN);
	if (IS_ERR(fpc->irq))
		return dev_err_probe(dev, PTR_ERR(fpc->irq), "interrupt GPIO\n");
	irq = gpiod_to_irq(fpc->irq);
	if (irq < 0)
		return irq;
	ret = devm_device_add_group(dev, &aura_fpc_group);
	if (ret)
		return ret;
	/* Request after sysfs creation; devres frees the IRQ before the attributes. */
	ret = devm_request_threaded_irq(dev, irq, NULL, aura_fpc_irq,
			IRQF_TRIGGER_RISING | IRQF_ONESHOT, dev_name(dev), fpc);
	if (ret)
		return dev_err_probe(dev, ret, "request interrupt\n");
	dev_info(dev, "electrical resources ready; sensor identity unverified\n");
	return 0;
}

static const struct of_device_id aura_fpc_match[] = {
	{ .compatible = "razer,aura-fpc-resources" },
	{ }
};
MODULE_DEVICE_TABLE(of, aura_fpc_match);

static struct platform_driver aura_fpc_driver = {
	.probe = aura_fpc_probe,
	.driver = {
		.name = "aura-fpc-resources",
		.of_match_table = aura_fpc_match,
	},
};
module_platform_driver(aura_fpc_driver);
MODULE_DESCRIPTION("Razer Phone 2 FPC reset and interrupt resources");
MODULE_LICENSE("GPL");
