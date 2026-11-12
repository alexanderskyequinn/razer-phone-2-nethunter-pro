from pathlib import Path
import difflib
root=Path(__file__).resolve().parents[1]
source=Path('/var/tmp/aura-kali-rootfs/var/tmp/aura-libcamera-work/libcamera-v0.7.2-191e202178f02430b5942397c70d215cdd2056fa')
changes={
'src/ipa/libipa/camera_sensor_helper.cpp':('class CameraSensorHelperImx415', '''// Razer stock helper at 0xbe8/0xc60 uses 512/(512-code), capped at code 480.
class CameraSensorHelperImx363 : public CameraSensorHelper
{
public:
    CameraSensorHelperImx363()
    {
        blackLevel_ = 4096;
        gain_ = AnalogueGainLinear{ 0, 512, -1, 512 };
    }
};
REGISTER_CAMERA_SENSOR_HELPER("imx363", CameraSensorHelperImx363)

'''),
'src/libcamera/sensor/camera_sensor_properties.cpp':('\t\t{ "imx415", {', '''        { "imx363", {
            .unitCellSize = { 1400, 1400 },
            /* Sensor-generated test patterns are not valid on this module. */
            .testPatternModes = {},
            .sensorDelays = {
                .exposureDelay = 2,
                .gainDelay = 2,
                .vblankDelay = 2,
                .hblankDelay = 2
            },
        } },
''')}
patch=[]
for rel,(anchor,addition) in changes.items():
    p=source/rel
    original=p.read_text()
    if 'CameraSensorHelperImx363' in original or '{ "imx363", {' in original:
        continue
    assert anchor in original
    new=original.replace(anchor,addition+anchor,1)
    p.write_text(new)
    patch.extend(difflib.unified_diff(original.splitlines(True),new.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
if patch:
    (root/'port/libcamera-imx363.patch').write_text(''.join(patch))
