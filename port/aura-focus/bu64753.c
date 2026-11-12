// SPDX-License-Identifier: GPL-2.0-only
/* Razer RC2 main lens; register sequence from its retained stock module data. */
#include <linux/delay.h>
#include <linux/i2c.h>
#include <linux/module.h>
#include <linux/pm_runtime.h>
#include <linux/regulator/consumer.h>
#include <media/v4l2-async.h>
#include <media/v4l2-cci.h>
#include <media/v4l2-ctrls.h>
#include <media/v4l2-device.h>
#include <media/v4l2-event.h>

struct bu64753 {
    struct v4l2_subdev sd;
    struct v4l2_ctrl_handler controls;
    struct v4l2_ctrl *focus;
    struct regulator_bulk_data supplies[2];
    struct regmap *map;
};

/* Stock tuned initial 50 + 150 steps * 5 codes = 800. */
#define FOCUS_MIN 50
#define FOCUS_MAX 800
#define FOCUS_REG CCI_REG16(0x45)
static const struct cci_reg_sequence settings[] = {
    { CCI_REG16(0xf1), 0xfd00 }, { CCI_REG16(0xf2), 0x1878 },
    { CCI_REG16(0xf3), 0x0400 }, { CCI_REG16(0xf5), 0xfcc0 },
    { CCI_REG16(0xf8), 0x0000 }, { CCI_REG16(0xde), 0x0aaa },
    { CCI_REG16(0xdf), 0x6000 }, { CCI_REG16(0xbe), 0x5800 },
    { CCI_REG16(0xce), 0x8500 }, { CCI_REG16(0xb0), 0x1999 },
    { CCI_REG16(0xb1), 0x7fff }, { CCI_REG16(0xb2), 0x7fff },
    { CCI_REG16(0xb3), 0x8400 }, { CCI_REG16(0xd0), 0x0298 },
    { CCI_REG16(0xd1), 0x63c7 }, { CCI_REG16(0xd2), 0xae14 },
    { CCI_REG16(0xd3), 0x7fff }, { CCI_REG16(0xd4), 0x7fff },
    { CCI_REG16(0xd9), 0x0404 },
};
static struct bu64753 *to_lens(struct device *dev)
{
    return container_of(dev_get_drvdata(dev), struct bu64753, sd);
}
static int bu64753_resume(struct device *dev)
{
    struct bu64753 *lens = to_lens(dev);
    u64 status;
    int ret, tries;
    ret = regulator_bulk_enable(2, lens->supplies);
    if (ret) return ret;
    usleep_range(1000, 1500);
    ret = cci_write(lens->map, CCI_REG16(0x07), 0, NULL);
    if (ret) goto off;
    usleep_range(1000, 1500);
    ret = cci_write(lens->map, CCI_REG16(0x07), 0x80, NULL);
    if (ret) goto off;
    usleep_range(1000, 1500);
    for (tries = 0; tries < 100; tries++) {
        ret = cci_read(lens->map, CCI_REG16(0xf7), &status, NULL);
        if (ret) goto off;
        if (status == 4) break;
        usleep_range(1000, 1500);
    }
    if (tries == 100) { ret = -ETIMEDOUT; goto off; }
    ret = cci_multi_reg_write(lens->map, settings, ARRAY_SIZE(settings), NULL);
    if (ret) goto off;
    ret = cci_write(lens->map, FOCUS_REG, lens->focus->val, NULL);
    if (!ret) return 0;
off:
    regulator_bulk_disable(2, lens->supplies);
    return ret;
}
static int bu64753_suspend(struct device *dev)
{
    struct bu64753 *lens = to_lens(dev);
    /* Stock module has no de-init register writes. Power down the rails. */
    return regulator_bulk_disable(2, lens->supplies);
}
static int bu64753_control(struct v4l2_ctrl *control)
{
    struct bu64753 *lens = container_of(control->handler, struct bu64753, controls);
    int ret = pm_runtime_get_if_in_use(lens->sd.dev);
    if (ret <= 0) return ret < 0 ? ret : 0;
    ret = cci_write(lens->map, FOCUS_REG, control->val, NULL);
    pm_runtime_mark_last_busy(lens->sd.dev);
    pm_runtime_put_autosuspend(lens->sd.dev);
    return ret;
}
static const struct v4l2_ctrl_ops control_ops = { .s_ctrl = bu64753_control };
static int bu64753_open(struct v4l2_subdev *sd, struct v4l2_subdev_fh *fh)
{
    return pm_runtime_resume_and_get(sd->dev);
}
static int bu64753_close(struct v4l2_subdev *sd, struct v4l2_subdev_fh *fh)
{
    pm_runtime_mark_last_busy(sd->dev);
    pm_runtime_put_autosuspend(sd->dev);
    return 0;
}
static const struct v4l2_subdev_internal_ops internal_ops = {
    .open = bu64753_open, .close = bu64753_close,
};
static const struct v4l2_subdev_core_ops core_ops = {
    .log_status = v4l2_ctrl_subdev_log_status,
    .subscribe_event = v4l2_ctrl_subdev_subscribe_event,
    .unsubscribe_event = v4l2_event_subdev_unsubscribe,
};
static const struct v4l2_subdev_ops subdev_ops = { .core = &core_ops };
static int bu64753_probe(struct i2c_client *client)
{
    struct device *dev = &client->dev;
    struct bu64753 *lens;
    int ret;
    lens = devm_kzalloc(dev, sizeof(*lens), GFP_KERNEL);
    if (!lens) return -ENOMEM;
    lens->map = devm_cci_regmap_init_i2c(client, 8);
    if (IS_ERR(lens->map)) return PTR_ERR(lens->map);
    lens->supplies[0].supply = "vcc";
    lens->supplies[1].supply = "vio";
    ret = devm_regulator_bulk_get(dev, 2, lens->supplies);
    if (ret) return dev_err_probe(dev, ret, "focus supplies unavailable\n");
    v4l2_i2c_subdev_init(&lens->sd, client, &subdev_ops);
    lens->sd.flags |= V4L2_SUBDEV_FL_HAS_DEVNODE | V4L2_SUBDEV_FL_HAS_EVENTS;
    lens->sd.internal_ops = &internal_ops;
    lens->sd.entity.function = MEDIA_ENT_F_LENS;
    v4l2_ctrl_handler_init(&lens->controls, 1);
    lens->focus = v4l2_ctrl_new_std(&lens->controls, &control_ops,
        V4L2_CID_FOCUS_ABSOLUTE, FOCUS_MIN, FOCUS_MAX, 1, FOCUS_MIN);
    ret = lens->controls.error;
    if (ret) goto free_controls;
    lens->sd.ctrl_handler = &lens->controls;
    ret = media_entity_pads_init(&lens->sd.entity, 0, NULL);
    if (ret) goto free_controls;
    pm_runtime_set_autosuspend_delay(dev, 500);
    pm_runtime_use_autosuspend(dev);
    pm_runtime_set_suspended(dev);
    pm_runtime_enable(dev);
    ret = pm_runtime_resume_and_get(dev);
    if (ret < 0) goto disable_pm;
    ret = v4l2_async_register_subdev(&lens->sd);
    pm_runtime_mark_last_busy(dev);
    pm_runtime_put_autosuspend(dev);
    if (ret) goto disable_pm;
    dev_info(dev, "Razer BU64753 focus controller initialized\n");
    return 0;
disable_pm:
    pm_runtime_disable(dev);
    if (!pm_runtime_status_suspended(dev)) bu64753_suspend(dev);
    media_entity_cleanup(&lens->sd.entity);
free_controls:
    v4l2_ctrl_handler_free(&lens->controls);
    return ret;
}
static void bu64753_remove(struct i2c_client *client)
{
    struct bu64753 *lens = to_lens(&client->dev);
    v4l2_async_unregister_subdev(&lens->sd);
    pm_runtime_disable(&client->dev);
    if (!pm_runtime_status_suspended(&client->dev)) bu64753_suspend(&client->dev);
    media_entity_cleanup(&lens->sd.entity);
    v4l2_ctrl_handler_free(&lens->controls);
}
static const struct dev_pm_ops pm_ops = {
    SET_RUNTIME_PM_OPS(bu64753_suspend, bu64753_resume, NULL)
};
static const struct of_device_id of_match[] = {
    { .compatible = "rohm,bu64753" }, {},
};
MODULE_DEVICE_TABLE(of, of_match);
static struct i2c_driver bu64753_driver = {
    .driver = { .name = "bu64753", .of_match_table = of_match, .pm = &pm_ops },
    .probe = bu64753_probe, .remove = bu64753_remove,
};
module_i2c_driver(bu64753_driver);
MODULE_DESCRIPTION("Razer Phone 2 BU64753 lens focus driver");
MODULE_LICENSE("GPL");
