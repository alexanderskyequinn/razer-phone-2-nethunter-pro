"""Add a per-board voltage ceiling without changing other phones' defaults."""
import difflib, subprocess, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1])
name='drivers/input/misc/qcom-spmi-haptics.c'
original=subprocess.check_output(['git','-C',str(source),'show','HEAD:'+name],text=True)
updated=original.replace('\tu32 vmax;','\tu32 vmax;\n\tu32 vmax_limit;')
updated=updated.replace('clamp_t(u32, vmax_mv, HAP_VMAX_MIN_MV, HAP_VMAX_MAX_MV)', 'clamp_t(u32, vmax_mv, HAP_VMAX_MIN_MV, haptics->vmax_limit)')
needle='\t// We only support LRAs for now'
replacement='''\t/* Preserve the board motor's maximum drive voltage. */
\thaptics->vmax_limit = HAP_VMAX_MAX_MV;
\tret = of_property_read_u32(node, "qcom,vmax-mv", &val);
\tif (!ret) {
\t\tif (val < HAP_VMAX_MIN_MV || val > HAP_VMAX_MAX_MV)
\t\t\treturn dev_err_probe(&pdev->dev, -EINVAL, "Invalid motor voltage ceiling\\n");
\t\thaptics->vmax_limit = val;
\t}

'''+needle
assert needle in updated
updated=updated.replace(needle,replacement)
assert updated != original and updated.count('u32 vmax_limit;') == 1
path=source/name
assert path.read_text() in (original,updated), 'Unexpected pre-existing driver modifications'
path.write_text(updated)
(root/'port/qcom-spmi-haptics-voltage-limit.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),updated.splitlines(True),fromfile='a/'+name,tofile='b/'+name)))
print('Applied board-specific haptics voltage ceiling; default unchanged.')
