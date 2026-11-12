// SPDX-License-Identifier: GPL-2.0-only
/* Experimental Razer Phone 2 panel; command data comes from its live DT. */
#include <linux/delay.h>
#include <linux/gpio/consumer.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_graph.h>
#include <linux/regulator/consumer.h>
#include <drm/drm_mipi_dsi.h>
#include <drm/drm_connector.h>
#include <drm/drm_modes.h>
#include <drm/drm_panel.h>
#include <drm/display/drm_dsc.h>
#include "panel-razer-nt36830-commands.h"

struct aura_panel {
	struct drm_panel panel;
	struct mipi_dsi_device *dsi[2];
	struct drm_dsc_config dsc[2];
	struct regulator_bulk_data supplies[4];
	struct gpio_desc *reset;
};

static int aura_commands(struct aura_panel *ctx, const struct aura_panel_cmd *cmd,
			 size_t count, bool low_power)
{
	/* MSM synchronized writes trigger on DSI1 and broadcast to DSI0. */
	struct mipi_dsi_device *dsi = ctx->dsi[1];
	for (size_t i = 0; i < count; i++) {
		struct mipi_dsi_msg msg = {
			.channel = dsi->channel, .type = cmd[i].type,
			.flags = low_power ? MIPI_DSI_MSG_USE_LPM : 0,
			.tx_buf = cmd[i].data, .tx_len = cmd[i].length,
		};
		/* Keep original packet types, including two-byte generic LONG writes.
		 * The bonded DSI manager broadcasts this transfer to both links.
		 */
		ssize_t ret = dsi->host->ops->transfer(dsi->host, &msg);
		if (ret < 0) {
			dev_err(&dsi->dev, "panel command %zu type=%02x failed: %zd\n", i, cmd[i].type, ret);
			return ret;
		}
		if (cmd[i].delay_ms)
			msleep(cmd[i].delay_ms);
	}
	return 0;
}

static int aura_prepare(struct drm_panel *panel)
{
	struct aura_panel *ctx = container_of(panel, struct aura_panel, panel);
	int i, ret;
	/* The Razer decoder uses Qualcomm's original pre-SCR table, whose
	 * first 10-bpc range max QP is 8 (upstream's VESA table uses 4).
	 * No PPS is sent to replace the decoder's table, so match it here,
	 * after the host fills the generic parameters and before DPU kickoff.
	 */
	for (i = 0; i < 2; i++) {
		struct drm_dsc_config *d = &ctx->dsc[i];
		d->rc_range_params[0].range_max_qp = 8;
		dev_info(panel->dev, "DSC%d: pic=%ux%u slice=%ux%u count=%u chunk=%u bpc=%u bpp=%u xmit=%u dec=%u scale=%u inc=%u decint=%u nfl=%u slice_bpg=%u initial=%u final=%u maxqp0=%u\n",
			i, d->pic_width, d->pic_height, d->slice_width, d->slice_height,
			d->slice_count, d->slice_chunk_size, d->bits_per_component,
			d->bits_per_pixel, d->initial_xmit_delay, d->initial_dec_delay,
			d->initial_scale_value, d->scale_increment_interval,
			d->scale_decrement_interval, d->nfl_bpg_offset, d->slice_bpg_offset,
			d->initial_offset, d->final_offset, d->rc_range_params[0].range_max_qp);
	}
	/* Preserve the captured order: VDDIO, external clock, IBB, LAB. */
	for (i = 0; i < ARRAY_SIZE(ctx->supplies); i++) {
		ret = regulator_enable(ctx->supplies[i].consumer);
		if (ret) goto rollback;
		/* Live stock DT: VDDIO and IBB each settle for 20 ms before
		 * the next rail/reset step. Regulator ramp time alone does not
		 * implement this panel-specific post-enable delay.
		 */
		if (i == 0 || i == 2)
			msleep(20);
	}
	gpiod_set_value_cansleep(ctx->reset, 0); msleep(10);
	gpiod_set_value_cansleep(ctx->reset, 1); msleep(10);
	gpiod_set_value_cansleep(ctx->reset, 0); msleep(10);
	/* Decoder parameters are vendor-programmed by this sequence. The stock
	 * driver explicitly suppresses standard PPS transmission for this panel.
	 */
	ret = aura_commands(ctx, aura_on, ARRAY_SIZE(aura_on), false);
	if (!ret) {
		dev_info(panel->dev, "Razer NT36830 initialization completed\n");
		return 0;
	}
	gpiod_set_value_cansleep(ctx->reset, 1);
rollback:
	while (i-- > 0) regulator_disable(ctx->supplies[i].consumer);
	return ret;
}

static int aura_unprepare(struct drm_panel *panel)
{
	struct aura_panel *ctx = container_of(panel, struct aura_panel, panel);
	int ret = aura_commands(ctx, aura_off, ARRAY_SIZE(aura_off), true);
	gpiod_set_value_cansleep(ctx->reset, 1);
	for (int i = ARRAY_SIZE(ctx->supplies) - 1; i >= 0; i--) {
		/* Stock pre-off delays for EXCLK/VDDIO, post-off for IBB. */
		if (i == 0 || i == 1)
			msleep(1);
		regulator_disable(ctx->supplies[i].consumer);
		if (i == 2)
			msleep(5);
	}
	return ret;
}

static const struct drm_display_mode aura_mode = {
	/* Command-mode porches represent transfer overhead, not panel blanking.
	 * With RGB888 input and 10-bpc DSC, this yields the captured 531-Mbps
	 * per-lane clock in dsi_adjust_pclk_for_compression(), at about 120 Hz:
	 * 504916000 * (1626 - 1440 + 384) / 1626 / 2 * 24 / 4.
	 */
	.clock = 504916,
	.hdisplay = 1440, .hsync_start = 1586, .hsync_end = 1602, .htotal = 1626,
	.vdisplay = 2560, .vsync_start = 2576, .vsync_end = 2578, .vtotal = 2592,
	.width_mm = 71, .height_mm = 126,
};

static int aura_get_modes(struct drm_panel *panel, struct drm_connector *connector)
{
	struct drm_display_mode *mode = drm_mode_duplicate(connector->dev, &aura_mode);
	if (!mode) return -ENOMEM;
	mode->type = DRM_MODE_TYPE_DRIVER | DRM_MODE_TYPE_PREFERRED;
	drm_mode_set_name(mode);
	drm_mode_probed_add(connector, mode);
	connector->display_info.width_mm = 71;
	connector->display_info.height_mm = 126;
	connector->display_info.bpc = 8; /* RGB888 input, DSC encoder uses 10 bpc. */
	return 1;
}

static const struct drm_panel_funcs aura_funcs = {
	.prepare = aura_prepare, .unprepare = aura_unprepare, .get_modes = aura_get_modes,
};

static void aura_unregister_secondary(void *data)
{
	mipi_dsi_device_unregister(data);
}

static int aura_probe(struct mipi_dsi_device *dsi)
{
	static const char * const names[] = { "vddio", "exclk", "ibb", "lab" };
	struct mipi_dsi_device_info info = { .type = "aura-secondary", .channel = 0 };
	struct aura_panel *ctx;
	struct device_node *node;
	struct mipi_dsi_host *host;
	int ret;

	ctx = devm_kzalloc(&dsi->dev, sizeof(*ctx), GFP_KERNEL);
	if (!ctx) return -ENOMEM;
	node = of_graph_get_remote_node(dsi->dev.of_node, 1, -1);
	if (!node) return -ENODEV;
	host = of_find_mipi_dsi_host_by_node(node);
	of_node_put(node);
	if (!host) return -EPROBE_DEFER;
	ctx->dsi[0] = dsi;
	ctx->dsi[1] = mipi_dsi_device_register_full(host, &info);
	if (IS_ERR(ctx->dsi[1])) return PTR_ERR(ctx->dsi[1]);
	ret = devm_add_action_or_reset(&dsi->dev, aura_unregister_secondary, ctx->dsi[1]);
	if (ret) return ret;
	for (int i = 0; i < ARRAY_SIZE(names); i++) ctx->supplies[i].supply = names[i];
	ret = devm_regulator_bulk_get(&dsi->dev, ARRAY_SIZE(ctx->supplies), ctx->supplies);
	if (ret) return dev_err_probe(&dsi->dev, ret, "panel supplies unavailable\n");
	ctx->reset = devm_gpiod_get(&dsi->dev, "reset", GPIOD_OUT_HIGH);
	if (IS_ERR(ctx->reset)) return PTR_ERR(ctx->reset);
	drm_panel_init(&ctx->panel, &dsi->dev, &aura_funcs, DRM_MODE_CONNECTOR_DSI);
	ctx->panel.prepare_prev_first = true;
	ret = drm_panel_of_backlight(&ctx->panel);
	if (ret) return ret;
	mipi_dsi_set_drvdata(dsi, ctx);
	drm_panel_add(&ctx->panel);
	for (int i = 0; i < 2; i++) {
		ctx->dsc[i] = (struct drm_dsc_config) {
			.dsc_version_major = 1, .dsc_version_minor = 1,
			.slice_height = 8, .slice_width = 720, .slice_count = 1,
			.bits_per_component = 10, .bits_per_pixel = 8 << 4,
			.block_pred_enable = true,
		};
		ctx->dsi[i]->dsc = &ctx->dsc[i];
		ctx->dsi[i]->lanes = 4;
		ctx->dsi[i]->format = MIPI_DSI_FMT_RGB888;
		ctx->dsi[i]->mode_flags = MIPI_DSI_CLOCK_NON_CONTINUOUS;
	}
	/* Attaching the primary can immediately start the framebuffer client. */
	for (int i = 1; i >= 0; i--) {
		ret = devm_mipi_dsi_attach(&dsi->dev, ctx->dsi[i]);
		if (ret) {
			drm_panel_remove(&ctx->panel);
			return ret;
		}
	}
	dev_info(&dsi->dev, "Razer dual-DSI DSC panel registered (experimental)\n");
	return 0;
}

static void aura_remove(struct mipi_dsi_device *dsi)
{
	struct aura_panel *ctx = mipi_dsi_get_drvdata(dsi);
	drm_panel_remove(&ctx->panel);
}

static const struct of_device_id aura_match[] = {
	{ .compatible = "razer,aura-nt36830" }, { }
};
MODULE_DEVICE_TABLE(of, aura_match);
static struct mipi_dsi_driver aura_driver = {
	.probe = aura_probe, .remove = aura_remove,
	.driver = { .name = "panel-razer-nt36830", .of_match_table = aura_match },
};
module_mipi_dsi_driver(aura_driver);
MODULE_DESCRIPTION("Experimental Razer Phone 2 NT36830 dual-DSI panel");
MODULE_LICENSE("GPL");
