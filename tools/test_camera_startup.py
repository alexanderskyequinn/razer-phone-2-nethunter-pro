"""Exercise the actual driver ID function against transient reads and faults."""
from pathlib import Path
import re,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
source=(root/'port/aura-camera/imx363.c').read_text()
function=re.search(r'static int imx363_identify_module\(.*?^}',source,re.S|re.M).group()
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stddef.h>
typedef unsigned long long u64;
struct i2c_client { int dev; } mock_client;
struct imx363 { int sd; void *regmap; } sensor;
#define IMX363_REG_CHIP_ID 0x16
#define IMX363_CHIP_ID 0x363
#define v4l2_get_subdevdata(x) (&mock_client)
#define dev_err(dev, ...) ((void)(dev))
static int reads,waits,results[3];
static u64 values[3];
static int cci_read(void *map,int reg,u64 *out,void *error) {
  (void)map;(void)error;assert(reg==0x16);assert(reads<3);
  *out=values[reads];return results[reads++];
}
static void usleep_range(int lo,int hi) {assert(lo==10000 && hi==11000);waits++;}
'''
suffix=r'''
static void check(int a,int b,int c,u64 x,u64 y,u64 z,int expected,int count) {
  results[0]=a;results[1]=b;results[2]=c;values[0]=x;values[1]=y;values[2]=z;
  reads=waits=0;assert(imx363_identify_module(&sensor)==expected);
  assert(reads==count);assert(waits==count-1);
}
int main(void) {
  check(0,0,0,0x363,0,0,0,1);
  check(0,0,0,0x333,0x363,0,0,2);
  check(-EIO,0,0,0,0x363,0,0,2);
  check(0,0,0,0x333,0x333,0x333,-EIO,3);
  check(-ETIMEDOUT,-ETIMEDOUT,-ETIMEDOUT,0,0,0,-ETIMEDOUT,3);
  check(0,0,-ENXIO,0x333,0x333,0,-ENXIO,3);
  check(0,0,0,0x333,0x333,0x363,0,3);
  return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='aura-camera-test-') as work:
    p=Path(work);(p/'test.c').write_text(prefix+function+suffix)
    subprocess.run(['gcc','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-o',str(p/'test'),str(p/'test.c')],check=True)
    subprocess.run([str(p/'test')],check=True)
print('Seven real-function camera identity/fault tests passed with ASan/UBSan.')
