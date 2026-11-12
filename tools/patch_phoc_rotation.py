"""Opt-in live rotation without the layout transaction's black cover."""
import difflib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = Path('/var/tmp/aura-kali-rootfs/var/tmp/aura-phoc-source/src/output.c')
original = Path('/var/tmp/aura-phoc-source/src/output.c').read_text()
old = '    if (configure_sent &&\n        !priv->modeset_shield &&'
new = '''    /* Keep orientation changes visible while layer clients resize.  On aura,
     * hiding them behind the modeset shield can expose the full transaction
     * timeout as a black screen.  Existing startup/lock shields stay intact.
     */
    if (configure_sent &&
        !(g_strcmp0 (g_getenv ("PHOC_AURA_LIVE_ROTATION"), "1") == 0 &&
          (event->state->committed & WLR_OUTPUT_STATE_TRANSFORM)) &&
        !priv->modeset_shield &&'''
assert original.count(old) == 1
updated = original.replace(old, new)
assert source.read_text() in (original, updated)
source.write_text(updated)
(root/'port/phoc-live-rotation.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True), updated.splitlines(True), fromfile='a/src/output.c', tofile='b/src/output.c')))
