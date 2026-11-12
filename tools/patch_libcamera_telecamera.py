"""IMX351 software ISP helper using the retained sensor's black level and gain."""
from pathlib import Path
import difflib
root = Path(__file__).resolve().parents[1]
source = Path('/var/tmp/aura-kali-rootfs/var/tmp/aura-libcamera-work/libcamera-v0.7.2-191e202178f02430b5942397c70d215cdd2056fa')
relative = 'src/ipa/libipa/camera_sensor_helper.cpp'
path = source/relative
old = path.read_text()
if 'CameraSensorHelperImx351' in old:
    print('IMX351 helper already present')
    raise SystemExit(0)
anchor = 'class CameraSensorHelperImx363 : public CameraSensorHelper'
assert old.count(anchor) == 1
new = old.replace(anchor, '''// IMX351: stock black level64 in RAW10; gain1024/(1024-code).
class CameraSensorHelperImx351 : public CameraSensorHelper
{
public:
    CameraSensorHelperImx351()
    {
        blackLevel_ = 4096;
        gain_ = AnalogueGainLinear{ 0, 1024, -1, 1024 };
    }
};
REGISTER_CAMERA_SENSOR_HELPER("imx351", CameraSensorHelperImx351)

''' + anchor)
path.write_text(new)
(root/'port/libcamera-imx351.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))
print('Applied IMX351 gain and black-level helper')
