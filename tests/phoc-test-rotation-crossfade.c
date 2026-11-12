/* Render-level regression: delay app resize, then cover it with an overlay. */
#include "testlib.h"
#include "testlib-layer-shell.h"
#include "output.h"
#include "phoc-animation.h"

typedef struct {
  PhocServer *server;
  gint rotated;
  enum wl_output_transform transform;
} RotationTest;

static gboolean
rotate_on_server (gpointer data)
{
  RotationTest *test = data;
  PhocDesktop *desktop = phoc_server_get_desktop (test->server);
  PhocOutput *output = wl_container_of (desktop->outputs.next, output, link);
  struct wlr_output_state state = {0};

  wlr_output_state_set_transform (&state, test->transform);
  g_assert_true (wlr_output_commit_state (output->wlr_output, &state));
  wlr_output_state_finish (&state);
  g_atomic_int_set (&test->rotated, 1);
  return G_SOURCE_REMOVE;
}

static void
rotate (RotationTest *test, enum wl_output_transform transform)
{
  test->transform = transform;
  g_atomic_int_set (&test->rotated, 0);
  g_idle_add (rotate_on_server, test);
  while (!g_atomic_int_get (&test->rotated))
    g_usleep (1000);
}

static void
assert_color (PhocTestClientGlobals *globals, guint32 color)
{
  PhocTestBuffer *frame = phoc_test_client_capture_output (globals, &globals->output);
  /* Sample both halves, excluding window edges and decorations. */
  for (guint y = frame->height / 4; y <= frame->height * 3 / 4; y += frame->height / 4) {
    for (guint x = frame->width / 4; x <= frame->width * 3 / 4; x += frame->width / 4) {
      guint32 pixel = *(guint32 *)(frame->shm_data + y * frame->stride + x * 4);
      g_assert_cmphex (pixel & 0xffffff, ==, color & 0xffffff);
    }
  }
  phoc_test_buffer_free (frame);
}

static gboolean
prepare (PhocServer *server, gpointer data)
{
  RotationTest *test = data;
  g_autoptr (GSettings) settings = g_settings_new ("mobi.phosh.phoc");
  test->server = server;
  PhocDesktop *desktop = phoc_server_get_desktop (server);
  PhocOutput *output;
  wl_list_for_each (output, &desktop->outputs, link)
    phoc_output_lower_shield (output, PHOC_EASING_EASE_OUT_QUINT, 0);
  phoc_desktop_set_auto_maximize (phoc_server_get_desktop (server), TRUE);
  g_settings_set_boolean (settings, "focus-frame", FALSE);
  return TRUE;
}

static gboolean
run_client (PhocTestClientGlobals *globals, gpointer data)
{
  RotationTest *test = data;
  PhocTestXdgToplevelSurface *app;
  PhocTestLayerSurface *overlay;

  app = phoc_test_xdg_toplevel_new_with_buffer (globals, 0, 0, "rotation-test", 0xffff0000);
  /* Let the startup shield finish its default 250 ms fade first. */
  g_usleep (400000);
  assert_color (globals, 0xffff0000);
  rotate (test, WL_OUTPUT_TRANSFORM_90);
  /* No new app buffer: the old whole frame must cover the incomplete layout. */
  assert_color (globals, 0xffff0000);
  wl_display_roundtrip (globals->display);
  phoc_test_xdg_update_buffer (globals, app, 0xff00ff00);
  wl_display_roundtrip (globals->display);
  g_usleep (600000);
  assert_color (globals, 0xff00ff00);

  rotate (test, WL_OUTPUT_TRANSFORM_NORMAL);
  overlay = phoc_test_layer_surface_new (globals, 0, 0, 0xff0000ff,
                ZWLR_LAYER_SURFACE_V1_ANCHOR_TOP | ZWLR_LAYER_SURFACE_V1_ANCHOR_BOTTOM |
                ZWLR_LAYER_SURFACE_V1_ANCHOR_LEFT | ZWLR_LAYER_SURFACE_V1_ANCHOR_RIGHT, -1);
  zwlr_layer_surface_v1_set_layer (overlay->layer_surface, ZWLR_LAYER_SHELL_V1_LAYER_OVERLAY);
  wl_surface_commit (overlay->wl_surface);
  wl_display_roundtrip (globals->display);
  /* A lockscreen-like overlay must win immediately, even during a resize. */
  assert_color (globals, 0xff0000ff);
  phoc_test_layer_surface_free (overlay);
  phoc_test_xdg_toplevel_free (app);
  return TRUE;
}

static void
test_rotation (void)
{
  RotationTest test = {0};
  PhocTestClientIface iface = {
    .server_prepare = prepare,
    .client_run = run_client,
    .debug_flags = PHOC_SERVER_DEBUG_FLAG_DISABLE_ANIMATIONS,
    .output_config = {.width = 320, .height = 480, .scale = 1},
  };
  phoc_test_client_run (TEST_PHOC_CLIENT_TIMEOUT, &iface, &test);
}

int main (int argc, char **argv)
{
  g_test_init (&argc, &argv, NULL);
  PHOC_TEST_ADD ("/phoc/aura/rotation-crossfade", test_rotation);
  return g_test_run ();
}
