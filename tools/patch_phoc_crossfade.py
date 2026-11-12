"""Build the crossfade candidate from the unmodified, pinned Phoc source."""
import difflib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
base = Path('/var/tmp/aura-phoc-source/src')
target = Path('/var/tmp/aura-kali-rootfs/var/tmp/aura-phoc-source/src')
patches = []

def replace(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)

original = (base/'output.c').read_text()
text = replace(original, '#include "layer-shell.h"', '#include "layer-shell.h"\n#include "layer-surface.h"')
text = replace(text, '#include <wlr/render/swapchain.h>', '#include <wlr/render/swapchain.h>\n#include <wlr/render/wlr_texture.h>\n#include <wlr/types/wlr_buffer.h>')
text = replace(text, '  gboolean modeset_shield;', '''  gboolean modeset_shield;
  struct wlr_buffer *rotation_buffer;
  struct wlr_texture *rotation_texture;
  gint64 rotation_started_us, rotation_fade_us;''')
text = replace(text, '\nstatic void\non_transaction_active_changed', '\n' + (root/'port/phoc-rotation-crossfade.c.inc').read_text() + '\nstatic void\non_transaction_active_changed')
text = replace(text, '  if (self->fullscreen_view)\n    scanned_out', '  if (self->fullscreen_view && !aura_rotation_enabled ())\n    scanned_out')
text = replace(text, '  pixman_region32_init (&buffer_damage);\n  wlr_damage_ring_rotate_buffer', '  if (priv->rotation_texture)\n    wlr_damage_ring_add_whole (&priv->damage_ring);\n\n  pixman_region32_init (&buffer_damage);\n  wlr_damage_ring_rotate_buffer')
text = replace(text, '  if (!wlr_output_commit_state (wlr_output, &pending))\n    goto out;\n\n out:', '  if (!wlr_output_commit_state (wlr_output, &pending))\n    goto out;\n\n  aura_rotation_remember (self, pending.buffer);\n\n out:')
text = replace(text, '  /* Want frame clock ticking as long as we have frame callbacks */', '  if (priv->rotation_texture)\n    phoc_output_damage_whole (self);\n\n  /* Want frame clock ticking as long as we have frame callbacks */')
text = replace(text, '  struct wlr_output_event_commit *event = data;\n', '''  struct wlr_output_event_commit *event = data;
  gboolean rotation = FALSE;

  if (event->state->committed & (WLR_OUTPUT_STATE_MODE | WLR_OUTPUT_STATE_ENABLED))
    aura_rotation_clear (self);
  if (event->state->committed & WLR_OUTPUT_STATE_TRANSFORM)
    rotation = aura_rotation_begin (self);
''')
text = replace(text, '    if (configure_sent &&\n        !priv->modeset_shield', '    if (configure_sent && !rotation &&\n        !priv->modeset_shield')
text = replace(text, '  self->wlr_output->data = NULL;', '  aura_rotation_clear (self);\n  self->wlr_output->data = NULL;')
text = replace(text, '  phoc_output_shield_raise (priv->shield, show_spinner);', '  aura_rotation_clear (self);\n  phoc_output_shield_raise (priv->shield, show_spinner);')

changes = {'output.c': text}
changes['render.c'] = replace((base/'render.c').read_text(), '  render_layer (ZWLR_LAYER_SHELL_V1_LAYER_OVERLAY, ctx);', '  phoc_output_render_rotation (output, ctx);\n  render_layer (ZWLR_LAYER_SHELL_V1_LAYER_OVERLAY, ctx);')
changes['render-private.h'] = replace((base/'render-private.h').read_text(), 'G_END_DECLS', 'void phoc_output_render_rotation (PhocOutput *self, PhocRenderContext *ctx);\n\nG_END_DECLS')
for filename, updated in changes.items():
    original = (base/filename).read_text()
    if (target/filename).read_text() != updated:
        (target/filename).write_text(updated)
    patches.extend(difflib.unified_diff(original.splitlines(True), updated.splitlines(True), fromfile='a/src/'+filename, tofile='b/src/'+filename))
(root/'port/phoc-rotation-crossfade.patch').write_text(''.join(patches))
testdir = target.parent/'tests'
test_source = (root/'tests/phoc-test-rotation-crossfade.c').read_text()
if not (testdir/'test-rotation-crossfade.c').exists() or (testdir/'test-rotation-crossfade.c').read_text() != test_source:
    (testdir/'test-rotation-crossfade.c').write_text(test_source)
meson = (base.parent/'tests/meson.build').read_text()
meson = replace(meson, "tests = [", "tests = [\n  'rotation-crossfade',")
if (testdir/'meson.build').read_text() != meson:
    (testdir/'meson.build').write_text(meson)
print('Patched output lifecycle, resize hold, and overlay-safe crossfade')
