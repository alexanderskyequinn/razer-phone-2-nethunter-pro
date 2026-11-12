// SPDX-License-Identifier: GPL-2.0-only
/* Razer Phone 2 IMX351, single retained 4208x3120 RAW10 mode.
 * Register tables: original Razer liteon_imx351 module.
 * Gain/exposure register semantics cross-checked against Rockchip IMX351.
 */
#include <linux/clk.h>
#include <linux/delay.h>
#include <linux/gpio/consumer.h>
#include <linux/i2c.h>
#include <linux/module.h>
#include <linux/pm_runtime.h>
#include <linux/regulator/consumer.h>
#include <media/v4l2-cci.h>
#include <media/v4l2-ctrls.h>
#include <media/v4l2-device.h>
#include <media/v4l2-fwnode.h>

#include "imx351_tables.h"
#define WIDTH 4208
#define HEIGHT 3120
#define PPL 8704
#define VTS 3188
/* VT PLL: 24 MHz / 4 * 347 / 2 / 5 * 4 = 832.8 MHz. */
#define PIXEL_RATE 832800000LL
static const s64 link_freq[] = { 528000000 };
static const char * const supplies[] = { "vana", "vdig", "vio" };

struct imx351 {
    struct v4l2_subdev sd;
    struct media_pad pad;
    struct regmap *map;
    struct clk *clock;
    struct gpio_desc *reset;
    struct regulator_bulk_data rails[3];
    struct v4l2_ctrl_handler controls;
    struct v4l2_ctrl *exposure, *vblank;
    struct mutex lock;
    bool streaming;
};
static inline struct imx351 *to_imx351(struct v4l2_subdev *sd)
{ return container_of(sd, struct imx351, sd); }

static int power_on(struct device *dev)
{
    struct imx351 *s = to_imx351(dev_get_drvdata(dev));
    unsigned int i;
    int ret;
    for (i = 0; i < ARRAY_SIZE(s->rails); ++i) {
        ret = regulator_enable(s->rails[i].consumer);
        if (ret) goto disable;
    }
    ret = clk_prepare_enable(s->clock);
    if (ret) goto disable;
    usleep_range(1000, 1500);
    gpiod_set_value_cansleep(s->reset, 0);
    msleep(11);
    return 0;
disable:
    while (i) regulator_disable(s->rails[--i].consumer);
    return ret;
}
static int power_off(struct device *dev)
{
    struct imx351 *s = to_imx351(dev_get_drvdata(dev));
    int i;
    gpiod_set_value_cansleep(s->reset, 1);
    usleep_range(1000, 1500);
    clk_disable_unprepare(s->clock);
    for (i = ARRAY_SIZE(s->rails) - 1; i >= 0; --i)
        regulator_disable(s->rails[i].consumer);
    return 0;
}
static int set_control(struct v4l2_ctrl *ctrl)
{
    struct imx351 *s = container_of(ctrl->handler, struct imx351, controls);
    struct device *dev = s->sd.dev;
    int ret;
    if (ctrl->id == V4L2_CID_VBLANK)
        __v4l2_ctrl_modify_range(s->exposure, 8, HEIGHT + ctrl->val - 10,
                                1, min_t(int, s->exposure->val, HEIGHT + ctrl->val - 10));
    ret = pm_runtime_get_if_in_use(dev);
    if (ret <= 0) return ret;
    switch (ctrl->id) {
    case V4L2_CID_EXPOSURE:
        ret = cci_write(s->map, CCI_REG16(0x0202), ctrl->val, NULL); break;
    case V4L2_CID_ANALOGUE_GAIN:
        ret = cci_write(s->map, CCI_REG16(0x0204), ctrl->val, NULL); break;
    case V4L2_CID_VBLANK:
        ret = cci_write(s->map, CCI_REG16(0x0340), HEIGHT + ctrl->val, NULL); break;
    default: ret = -EINVAL; break;
    }
    pm_runtime_put(dev);
    return ret;
}
static const struct v4l2_ctrl_ops ctrl_ops = { .s_ctrl = set_control };

static void fill_format(struct v4l2_mbus_framefmt *fmt)
{
    *fmt = (struct v4l2_mbus_framefmt) {
        .width = WIDTH, .height = HEIGHT, .code = MEDIA_BUS_FMT_SRGGB10_1X10,
        .field = V4L2_FIELD_NONE, .colorspace = V4L2_COLORSPACE_RAW,
        .ycbcr_enc = V4L2_YCBCR_ENC_DEFAULT, .quantization = V4L2_QUANTIZATION_FULL_RANGE,
        .xfer_func = V4L2_XFER_FUNC_NONE,
    };
}
static int init_state(struct v4l2_subdev *sd, struct v4l2_subdev_state *state)
{
    fill_format(v4l2_subdev_state_get_format(state, 0));
    return 0;
}
static int enum_code(struct v4l2_subdev *sd, struct v4l2_subdev_state *state,
                     struct v4l2_subdev_mbus_code_enum *code)
{
    if (code->pad || code->index) return -EINVAL;
    code->code = MEDIA_BUS_FMT_SRGGB10_1X10;
    return 0;
}
static int enum_size(struct v4l2_subdev *sd, struct v4l2_subdev_state *state,
                     struct v4l2_subdev_frame_size_enum *size)
{
    if (size->pad || size->index || size->code != MEDIA_BUS_FMT_SRGGB10_1X10)
        return -EINVAL;
    size->min_width = size->max_width = WIDTH;
    size->min_height = size->max_height = HEIGHT;
    return 0;
}
static int get_format(struct v4l2_subdev *sd, struct v4l2_subdev_state *state,
                      struct v4l2_subdev_format *fmt)
{
    if (fmt->pad) return -EINVAL;
    fill_format(&fmt->format);
    return 0;
}
static int set_format(struct v4l2_subdev *sd, struct v4l2_subdev_state *state,
                      struct v4l2_subdev_format *fmt)
{
    int ret = get_format(sd, state, fmt);
    if (!ret && fmt->which == V4L2_SUBDEV_FORMAT_TRY)
        *v4l2_subdev_state_get_format(state, 0) = fmt->format;
    return ret;
}
static int get_selection(struct v4l2_subdev *sd, struct v4l2_subdev_state *state,
                         struct v4l2_subdev_selection *sel)
{
    if (sel->pad) return -EINVAL;
    switch (sel->target) {
    case V4L2_SEL_TGT_NATIVE_SIZE:
        sel->r = (struct v4l2_rect){ 0, 0, 4656, 3496 }; break;
    case V4L2_SEL_TGT_CROP_BOUNDS:
    case V4L2_SEL_TGT_CROP_DEFAULT:
    case V4L2_SEL_TGT_CROP:
        sel->r = (struct v4l2_rect){ 224, 188, WIDTH, HEIGHT }; break;
    default: return -EINVAL;
    }
    return 0;
}
static int stream(struct v4l2_subdev *sd, int enable)
{
    struct imx351 *s = to_imx351(sd);
    int ret = 0;
    mutex_lock(&s->lock);
    if (s->streaming == !!enable) goto out;
    if (!enable) {
        ret = cci_write(s->map, CCI_REG8(0x0100), 0, NULL);
        s->streaming = false;
        pm_runtime_mark_last_busy(sd->dev);
        pm_runtime_put_autosuspend(sd->dev);
        goto out;
    }
    ret = pm_runtime_resume_and_get(sd->dev);
    if (ret < 0) goto out;
    ret = cci_write(s->map, CCI_REG8(0x0103), 1, NULL);
    if (ret) goto off;
    msleep(12);
    ret = cci_multi_reg_write(s->map, imx351_global, ARRAY_SIZE(imx351_global), NULL);
    if (ret) goto off;
    ret = cci_multi_reg_write(s->map, imx351_full, ARRAY_SIZE(imx351_full), NULL);
    if (ret) goto off;
    /* Original full mode uses no mirror/flip; keep Bayer order deterministic. */
    ret = cci_write(s->map, CCI_REG8(0x0101), 0, NULL);
    if (ret) goto off;
    ret = __v4l2_ctrl_handler_setup(&s->controls);
    if (ret) goto off;
    ret = cci_write(s->map, CCI_REG8(0x0100), 1, NULL);
    if (ret) goto off;
    s->streaming = true;
    goto out;
off:
    cci_write(s->map, CCI_REG8(0x0100), 0, NULL);
    pm_runtime_put_sync(sd->dev);
out:
    mutex_unlock(&s->lock);
    return ret;
}
static const struct v4l2_subdev_video_ops video_ops = { .s_stream = stream };
static const struct v4l2_subdev_pad_ops pad_ops = {
    .enum_mbus_code = enum_code, .enum_frame_size = enum_size,
    .get_fmt = get_format, .set_fmt = set_format, .get_selection = get_selection,
};
static const struct v4l2_subdev_ops subdev_ops = { .video = &video_ops, .pad = &pad_ops };
static const struct v4l2_subdev_internal_ops internal_ops = { .init_state = init_state };

static int init_controls(struct imx351 *s)
{
    struct v4l2_ctrl_handler *h = &s->controls;
    struct v4l2_fwnode_device_properties props;
    struct v4l2_ctrl *c;
    int ret = v4l2_ctrl_handler_init(h, 8);
    if (ret) return ret;
    h->lock = &s->lock;
    c = v4l2_ctrl_new_int_menu(h, NULL, V4L2_CID_LINK_FREQ, 0, 0, link_freq);
    if (c) c->flags |= V4L2_CTRL_FLAG_READ_ONLY;
    v4l2_ctrl_new_std(h, NULL, V4L2_CID_PIXEL_RATE, PIXEL_RATE, PIXEL_RATE, 1, PIXEL_RATE);
    c = v4l2_ctrl_new_std(h, NULL, V4L2_CID_HBLANK, PPL-WIDTH, PPL-WIDTH, 1, PPL-WIDTH);
    if (c) c->flags |= V4L2_CTRL_FLAG_READ_ONLY;
    s->exposure = v4l2_ctrl_new_std(h, &ctrl_ops, V4L2_CID_EXPOSURE, 8, VTS-10, 1, 1000);
    s->vblank = v4l2_ctrl_new_std(h, &ctrl_ops, V4L2_CID_VBLANK, VTS-HEIGHT, 65525-HEIGHT, 1, VTS-HEIGHT);
    /* Sensor code, gain = 1024 / (1024 - code), capped at 16x. */
    v4l2_ctrl_new_std(h, &ctrl_ops, V4L2_CID_ANALOGUE_GAIN, 0, 960, 1, 0);
    if (h->error) return h->error;
    ret = v4l2_fwnode_device_parse(s->sd.dev, &props);
    if (ret) return ret;
    ret = v4l2_ctrl_new_fwnode_properties(h, &ctrl_ops, &props);
    s->sd.ctrl_handler = h;
    return ret;
}
static int probe(struct i2c_client *client)
{
    struct device *dev = &client->dev;
    struct v4l2_fwnode_endpoint ep = { .bus_type = V4L2_MBUS_CSI2_DPHY };
    struct fwnode_handle *endpoint;
    struct imx351 *s;
    unsigned long bitmap;
    u64 id;
    int ret, i;
    s = devm_kzalloc(dev, sizeof(*s), GFP_KERNEL);
    if (!s) return -ENOMEM;
    mutex_init(&s->lock);
    s->map = devm_cci_regmap_init_i2c(client, 16);
    if (IS_ERR(s->map)) { ret = PTR_ERR(s->map); goto destroy; }
    s->reset = devm_gpiod_get(dev, "reset", GPIOD_OUT_HIGH);
    if (IS_ERR(s->reset)) { ret = PTR_ERR(s->reset); goto destroy; }
    s->clock = devm_clk_get(dev, "xvclk");
    if (IS_ERR(s->clock)) { ret = PTR_ERR(s->clock); goto destroy; }
    ret = clk_set_rate(s->clock, 24000000);
    if (ret) goto destroy;
    if (clk_get_rate(s->clock) != 24000000) { ret = -EINVAL; goto destroy; }
    for (i = 0; i < ARRAY_SIZE(s->rails); ++i) s->rails[i].supply = supplies[i];
    ret = devm_regulator_bulk_get(dev, ARRAY_SIZE(s->rails), s->rails);
    if (ret) goto destroy;
    endpoint = fwnode_graph_get_next_endpoint(dev_fwnode(dev), NULL);
    if (!endpoint) { ret = -EINVAL; goto destroy; }
    ret = v4l2_fwnode_endpoint_alloc_parse(endpoint, &ep);
    fwnode_handle_put(endpoint);
    if (ret) goto free_ep;
    if (ep.bus.mipi_csi2.num_data_lanes != 4) { ret = -EINVAL; goto free_ep; }
    ret = v4l2_link_freq_to_bitmap(dev, ep.link_frequencies, ep.nr_of_link_frequencies,
                                 link_freq, ARRAY_SIZE(link_freq), &bitmap);
    if (ret) goto free_ep;
    v4l2_fwnode_endpoint_free(&ep);
    v4l2_i2c_subdev_init(&s->sd, client, &subdev_ops);
    s->sd.internal_ops = &internal_ops;
    s->sd.flags |= V4L2_SUBDEV_FL_HAS_DEVNODE;
    s->sd.entity.function = MEDIA_ENT_F_CAM_SENSOR;
    s->pad.flags = MEDIA_PAD_FL_SOURCE;
    ret = power_on(dev);
    if (ret) goto destroy;
    ret = cci_read(s->map, CCI_REG16(0x0016), &id, NULL);
    power_off(dev);
    if (ret) goto destroy;
    if (id != 0x0351) { ret = -ENODEV; goto destroy; }
    ret = init_controls(s);
    if (ret) goto free_controls;
    ret = media_entity_pads_init(&s->sd.entity, 1, &s->pad);
    if (ret) goto free_controls;
    ret = v4l2_subdev_init_finalize(&s->sd);
    if (ret) goto free_entity;
    pm_runtime_set_suspended(dev);
    pm_runtime_set_autosuspend_delay(dev, 1000);
    pm_runtime_use_autosuspend(dev);
    pm_runtime_enable(dev);
    ret = v4l2_async_register_subdev_sensor(&s->sd);
    if (ret) goto disable_pm;
    dev_info(dev, "IMX351 identified; retained Razer 4208x3120 mode available\n");
    return 0;
disable_pm:
    pm_runtime_disable(dev);
    v4l2_subdev_cleanup(&s->sd);
free_entity:
    media_entity_cleanup(&s->sd.entity);
free_controls:
    v4l2_ctrl_handler_free(&s->controls);
    goto destroy;
free_ep:
    v4l2_fwnode_endpoint_free(&ep);
destroy:
    mutex_destroy(&s->lock);
    return dev_err_probe(dev, ret, "IMX351 setup failed\n");
}
static void remove_sensor(struct i2c_client *client)
{
    struct v4l2_subdev *sd = i2c_get_clientdata(client);
    struct imx351 *s = to_imx351(sd);
    v4l2_async_unregister_subdev(sd);
    pm_runtime_disable(&client->dev);
    if (!pm_runtime_status_suspended(&client->dev)) power_off(&client->dev);
    pm_runtime_set_suspended(&client->dev);
    v4l2_subdev_cleanup(sd);
    media_entity_cleanup(&sd->entity);
    v4l2_ctrl_handler_free(&s->controls);
    mutex_destroy(&s->lock);
}
static const struct dev_pm_ops pm_ops = { SET_RUNTIME_PM_OPS(power_off, power_on, NULL) };
static const struct of_device_id matches[] = { { .compatible = "sony,imx351" }, { } };
MODULE_DEVICE_TABLE(of, matches);
static struct i2c_driver imx351_driver = {
    .driver = { .name = "imx351", .of_match_table = matches, .pm = &pm_ops },
    .probe = probe, .remove = remove_sensor,
};
module_i2c_driver(imx351_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Razer Phone 2 IMX351 telephoto capture bring-up");
