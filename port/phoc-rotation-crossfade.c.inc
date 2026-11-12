/* Aura experiment: retain one composed physical frame across client resize.
 * Overlay surfaces (including the lockscreen) and output shields always win.
 * The snapshot never leaves GPU memory and is not saved to disk.
 */
static gboolean
aura_rotation_enabled (void)
{
  return g_strcmp0 (g_getenv ("PHOC_AURA_ROTATION_CROSSFADE"), "1") == 0;
}

static void
aura_rotation_clear (PhocOutput *self)
{
  PhocOutputPrivate *priv = phoc_output_get_instance_private (self);

  g_clear_pointer (&priv->rotation_texture, wlr_texture_destroy);
  g_clear_pointer (&priv->rotation_buffer, wlr_buffer_unlock);
  priv->rotation_started_us = priv->rotation_fade_us = 0;
}

static gboolean
aura_rotation_has_overlay (PhocOutput *self)
{
  PhocLayerSurface *surface;

  wl_list_for_each (surface, &self->layer_surfaces, link) {
    if (surface->mapped && surface->layer == ZWLR_LAYER_SHELL_V1_LAYER_OVERLAY)
      return TRUE;
  }
  return FALSE;
}

static gboolean
aura_rotation_clients_ready (PhocOutput *self)
{
  PhocDesktop *desktop = phoc_server_get_desktop (phoc_server_get_default ());
  PhocWorkspace *workspace = phoc_desktop_get_active_workspace (desktop);
  PhocLayerSurface *surface;

  /* Ignore unrelated outputs and hidden surfaces, which may not commit until
   * they are shown. Unlike the global transaction, this cannot wait 3 seconds.
   */
  wl_list_for_each (surface, &self->layer_surfaces, link) {
    if (surface->mapped && surface->pending_serial)
      return FALSE;
  }
  for (GList *l = phoc_workspace_get_views (workspace)->head; l; l = l->next) {
    PhocView *view = PHOC_VIEW (l->data);
    struct wlr_xdg_surface *xdg;

    if (!view->wlr_surface || !phoc_desktop_view_check_visibility (desktop, view))
      continue;
    xdg = wlr_xdg_surface_try_from_wlr_surface (view->wlr_surface);
    if (xdg && (xdg->configure_idle || !wl_list_empty (&xdg->configure_list) ||
                xdg->current.configure_serial != xdg->scheduled_serial))
      return FALSE;
  }
  return TRUE;
}

static gboolean
aura_rotation_begin (PhocOutput *self)
{
  PhocOutputPrivate *priv = phoc_output_get_instance_private (self);

  if (!aura_rotation_enabled () || !priv->rotation_buffer ||
      aura_rotation_has_overlay (self) || phoc_output_shield_is_raised (priv->shield))
    return FALSE;
  if (priv->rotation_buffer->width != self->wlr_output->width ||
      priv->rotation_buffer->height != self->wlr_output->height) {
    aura_rotation_clear (self);
    return FALSE;
  }
  if (!priv->rotation_texture)
    priv->rotation_texture = wlr_texture_from_buffer (self->wlr_output->renderer,
                                                      priv->rotation_buffer);
  if (!priv->rotation_texture) {
    aura_rotation_clear (self);
    return FALSE;
  }
  priv->rotation_started_us = g_get_monotonic_time ();
  priv->rotation_fade_us = 0;
  g_debug ("Aura rotation: retaining complete frame");
  return TRUE;
}

/* Called before the overlay layer and the existing output shield. */
void
phoc_output_render_rotation (PhocOutput *self, PhocRenderContext *ctx)
{
  PhocOutputPrivate *priv = phoc_output_get_instance_private (self);
  gint64 now;
  float alpha, progress;

  if (!priv->rotation_texture)
    return;
  if (aura_rotation_has_overlay (self) || phoc_output_shield_is_raised (priv->shield)) {
    aura_rotation_clear (self);
    return;
  }

  now = g_get_monotonic_time ();
  if (!priv->rotation_fade_us &&
      ((now - priv->rotation_started_us >= 30000 && aura_rotation_clients_ready (self)) ||
       now - priv->rotation_started_us >= 300000)) {
    priv->rotation_fade_us = now;
    g_debug ("Aura rotation: resize hold %" G_GINT64_FORMAT "ms",
             (now - priv->rotation_started_us) / 1000);
  }
  progress = priv->rotation_fade_us ? (now - priv->rotation_fade_us) / 150000.0f : 0.0f;
  if (progress >= 1.0f) {
    aura_rotation_clear (self);
    g_debug ("Aura rotation: crossfade finished");
    return;
  }
  alpha = 1.0f - progress * progress * (3.0f - 2.0f * progress);
  wlr_render_pass_add_texture (ctx->render_pass, &(struct wlr_render_texture_options) {
    .texture = priv->rotation_texture,
    .dst_box = { .width = self->wlr_output->width, .height = self->wlr_output->height },
    .alpha = &alpha,
    .clip = ctx->damage,
    .transform = WL_OUTPUT_TRANSFORM_NORMAL,
  });
}

static void
aura_rotation_remember (PhocOutput *self, struct wlr_buffer *buffer)
{
  PhocOutputPrivate *priv = phoc_output_get_instance_private (self);

  if (!aura_rotation_enabled ())
    return;
  if (aura_rotation_has_overlay (self) || phoc_output_shield_is_raised (priv->shield)) {
    aura_rotation_clear (self);
    return;
  }
  if (priv->rotation_texture)
    return;
  /* Lock before releasing the preceding frame, including if they are equal. */
  wlr_buffer_lock (buffer);
  g_clear_pointer (&priv->rotation_buffer, wlr_buffer_unlock);
  priv->rotation_buffer = buffer;
}
