// SPDX-License-Identifier: GPL-2.0-only
/* Razer RC2 telephoto lens; register sequence from its retained stock module data. */
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

struct lc898217 {
    struct v4l2_subdev sd;
    struct v4l2_ctrl_handler controls;
    struct v4l2_ctrl *focus;
    struct regulator_bulk_data supplies[2];
    struct regmap *map;
};

/* Stock tuned initial 60 + 110 steps * 5 codes = 610. */
#define FOCUS_MIN 60
#define FOCUS_MAX 610
#define FOCUS_REG CCI_REG16(0x84)
static struct lc898217 *to_lens(struct device *dev)
{
    return container_of(dev_get_drvdata(dev), struct lc898217, sd);
}
static int lc898217_resume(struct device *dev)
{
    struct lc898217 *lens = to_lens(dev);
    u64 status;
    int ret, tries;
    ret = regulator_bulk_enable(2, lens->supplies);
    if (ret) return ret;
    /* Stock power-on wait8ms; poll ID0xf0=0x72, then initialize ROM servo. */
    msleep(8);
    ret = cci_read(lens->map, CCI_REG8(0xf0), &status, NULL);
    if (ret) goto off;
    if (status != 0x72) { ret = -ENODEV; goto off; }
    ret = cci_write(lens->map, CCI_REG8(0xe0), 1, NULL);
    if (ret) goto off;
    for (tries = 0; tries < 100; ++tries) {
        ret = cci_read(lens->map, CCI_REG8(0xe3), &status, NULL);
        if (ret) goto off;
        if (status == 0) break;
        usleep_range(1000, 1500);
    }
    if (tries == 100) { ret = -ETIMEDOUT; goto off; }
    ret = cci_write(lens->map, FOCUS_REG, lens->focus->val, NULL);
    if (!ret) return 0;
off:
    regulator_bulk_disable(2, lens->supplies);
    return ret;
}
static int lc898217_suspend(struct device *dev)
{
    struct lc898217 *lens = to_lens(dev);
    /* Stock module has no de-init register writes. Power down the rails. */
    return regulator_bulk_disable(2, lens->supplies);
}
static int lc898217_control(struct v4l2_ctrl *control)
{
    struct lc898217 *lens = container_of(control->handler, struct lc898217, controls);
    int ret = pm_runtime_get_if_in_use(lens->sd.dev);
    if (ret <= 0) return ret < 0 ? ret : 0;
    ret = cci_write(lens->map, FOCUS_REG, control->val, NULL);
    pm_runtime_mark_last_busy(lens->sd.dev);
    pm_runtime_put_autosuspend(lens->sd.dev);
    return ret;
}
static const struct v4l2_ctrl_ops control_ops = { .s_ctrl = lc898217_control };
static int lc898217_open(struct v4l2_subdev *sd, struct v4l2_subdev_fh *fh)
{
    return pm_runtime_resume_and_get(sd->dev);
}
static int lc898217_close(struct v4l2_subdev *sd, struct v4l2_subdev_fh *fh)
{
    pm_runtime_mark_last_busy(sd->dev);
    pm_runtime_put_autosuspend(sd->dev);
    return 0;
}
static const struct v4l2_subdev_internal_ops internal_ops = {
    .open = lc898217_open, .close = lc898217_close,
};
static const struct v4l2_subdev_core_ops core_ops = {
    .log_status = v4l2_ctrl_subdev_log_status,
    .subscribe_event = v4l2_ctrl_subdev_subscribe_event,
    .unsubscribe_event = v4l2_event_subdev_unsubscribe,
};
static const struct v4l2_subdev_ops subdev_ops = { .core = &core_ops };
static int lc898217_probe(struct i2c_client *client)
{
    struct device *dev = &client->dev;
    struct lc898217 *lens;
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
    dev_info(dev, "Razer LC898217XC focus controller initialized\n");
    return 0;
disable_pm:
    pm_runtime_disable(dev);
    if (!pm_runtime_status_suspended(dev)) lc898217_suspend(dev);
    media_entity_cleanup(&lens->sd.entity);
free_controls:
    v4l2_ctrl_handler_free(&lens->controls);
    return ret;
}
static void lc898217_remove(struct i2c_client *client)
{
    struct lc898217 *lens = to_lens(&client->dev);
    v4l2_async_unregister_subdev(&lens->sd);
    pm_runtime_disable(&client->dev);
    if (!pm_runtime_status_suspended(&client->dev)) lc898217_suspend(&client->dev);
    media_entity_cleanup(&lens->sd.entity);
    v4l2_ctrl_handler_free(&lens->controls);
}
static const struct dev_pm_ops pm_ops = {
    SET_RUNTIME_PM_OPS(lc898217_suspend, lc898217_resume, NULL)
};
static const struct of_device_id of_match[] = {
    { .compatible = "onnn,lc898217xc" }, {},
};
MODULE_DEVICE_TABLE(of, of_match);
static struct i2c_driver lc898217_driver = {
    .driver = { .name = "lc898217", .of_match_table = of_match, .pm = &pm_ops },
    .probe = lc898217_probe, .remove = lc898217_remove,
};
module_i2c_driver(lc898217_driver);
MODULE_DESCRIPTION("Razer Phone 2 LC898217XC lens focus driver");
MODULE_LICENSE("GPL");
