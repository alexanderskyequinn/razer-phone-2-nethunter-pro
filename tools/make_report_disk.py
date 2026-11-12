"""Build a blank 16 MiB FAT16 report disk, entirely on the build host.

REPORT.TXT owns the first 1 MiB of the data area, offset 289 * 512.
The phone fills it before exposing the file as a read-only USB LUN.
"""
import gzip
from pathlib import Path
import struct

image = bytearray(16 * 1024 * 1024)
image[:11] = b'\xeb\x3c\x90AURADIAG'
struct.pack_into('<HBHBHHBHHHII', image, 11,
                 512, 1, 1, 2, 512, 32768, 0xf8, 128, 32, 64, 0, 0)
image[36:39] = b'\x80\x00\x29'
struct.pack_into('<I', image, 39, 0x84500005)
image[43:54] = b'AURA REPORT'
image[54:62] = b'FAT16   '
image[510:512] = b'\x55\xaa'
fat = bytearray(128 * 512)
struct.pack_into('<HH', fat, 0, 0xfff8, 0xffff)
for cluster in range(2, 2050):
    struct.pack_into('<H', fat, cluster * 2, cluster + 1 if cluster < 2049 else 0xffff)
image[512:129*512] = fat
image[129*512:257*512] = fat
root = 257 * 512
image[root:root+11] = b'AURA REPORT'
image[root+11] = 0x08
entry = root + 32
image[entry:entry+11] = b'REPORT  TXT'
image[entry+11] = 0x01  # read-only
struct.pack_into('<H', image, entry+26, 2)
struct.pack_into('<I', image, entry+28, 1024*1024)
image[289*512:289*512+30] = b'Awaiting native report.\r\n'.ljust(30)
out = Path(__file__).resolve().parents[1] / 'build/diagnostic'
(out/'report-template.img').write_bytes(image)
(out/'report-template.img.gz').write_bytes(gzip.compress(image, mtime=0))
print('FAT16 template ready; report capacity 1 MiB, data offset 147968.')
