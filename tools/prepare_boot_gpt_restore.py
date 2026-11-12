"""Prepare ONLY the phone's saved LUN4 GPT in the verified factory wire format.

No device I/O. No partition contents, geometry changes, or generic factory GPT.
"""
import hashlib,json,struct,tarfile,zlib
from pathlib import Path
from validate_gpt_backup import read_backup

root=Path(__file__).resolve().parents[1]
source=root/'device-data/native-prerequisites/gpt-after-qbootctl-v4-full.tar'
tables=read_backup(source,allow_stale_retry=True,allow_stale_crc=True)
with tarfile.open(source) as t:
    meta=json.load(t.extractfile('aura-gpt-backup/manifest.json'))
    start=t.extractfile('aura-gpt-backup/sde.start.bin').read()
assert hashlib.sha256(start).hexdigest()==meta['sde.start.bin']['sha256']
sector=4096
density=meta['sde.start.bin']['device_size']
assert density==746586112
sectors=density//sector
header=bytearray(start[sector:2*sector])
assert header[:8]==b'EFI PART'
assert struct.unpack_from('<QQQQ',header,24)==(1,sectors-1,6,sectors-34)
lba,count,size,crc=struct.unpack_from('<QIII',header,72)
assert (lba,count,size)==(2,64,128)
entries=start[lba*sector:lba*sector+count*size]
assert zlib.crc32(entries)==crc
assert len(tables['sde'])==53
last=tables['sde'][-1]
assert last['name']=='resv4' and last['last']==sectors-34
assert next(e for e in tables['sde'] if e['name']=='boot_b')['type']=='867f112085e95743b9ee374bc1d8487d'
assert next(e for e in tables['sde'] if e['name']=='boot_a')['type']=='d46c0377d503bb428ed137e5a88baa34'
assert next(e for e in tables['sde'] if e['name']=='boot_b')['attrs'] & (1<<54)

def crc_header(h):
    struct.pack_into('<I',h,16,0)
    length=struct.unpack_from('<I',h,12)[0]
    assert length==92
    struct.pack_into('<I',h,16,zlib.crc32(h[:length]))
    return h

backup=bytearray(header)
struct.pack_into('<QQ',backup,24,sectors-1,1)
struct.pack_into('<Q',backup,72,sectors-33)
crc_header(backup)
# The factory writer requires at least 16 KiB per entry-array buffer, even
# when the on-disk table describes 64 x 128-byte entries.
padded=entries+bytes(16384-len(entries))
image=start[:sector]+crc_header(header)+padded+padded+backup
assert len(image)==45056
# Independently parse both wire-format headers and their own arrays.
for pos,arraypos in [(4096,8192),(40960,24576)]:
    h=bytearray(image[pos:pos+92]); saved=struct.unpack_from('<I',h,16)[0]
    struct.pack_into('<I',h,16,0)
    assert zlib.crc32(h)==saved
    assert zlib.crc32(image[arraypos:arraypos+8192])==struct.unpack_from('<I',h,88)[0]
assert image[8192:16384]==entries and image[24576:32768]==entries
out=root/'build/kali/boot-metadata-recovery'
out.mkdir(parents=True,exist_ok=True)
dest=out/'same-phone-gpt-both4.bin'
dest.write_bytes(image)
manifest=dict(source=str(source.relative_to(root)),target_lun=4,
              device_bytes=density,sector_bytes=sector,partitions=53,
              partition_entries_identical_to_saved_primary=True,
              geometry_changed=False,payload_partitions_included=False,
              last_partition_patch_preserves_existing_end=True,
              image_sha256=hashlib.sha256(image).hexdigest(),
              image_bytes=len(image),hardware_restore_verified=False,
              reference_factory_build='aura-p-release-3201, Oct 22 2020',
              factory_gpt_writer='abl.efi 0x316e0..0x32130: five BlockIo.WriteBlocks calls, four CalculateCrc32 calls, no erase call',
              caution='Use only on serial YOUR_DEVICE_SERIAL and only with the matching Razer factory writer. Not a generic GPT repair tool.')
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
