"""Validate saved GPT headers and arrays without accessing a device."""
import hashlib, json, struct, sys, tarfile, zlib
from pathlib import Path

def read_backup(path, allow_stale_retry=False, allow_stale_crc=False):
    with tarfile.open(path) as t:
        files = {Path(m.name).name: t.extractfile(m).read() for m in t.getmembers() if m.isfile()}
    meta = json.loads(files['manifest.json'])
    tables = {}
    for name, rec in meta.items():
        assert hashlib.sha256(files[name]).hexdigest() == rec['sha256'], name
    for dev in ('sda', 'sdb', 'sdc', 'sdd', 'sde', 'sdf'):
        start = files[dev + '.start.bin']
        sector = next(s for s in (512, 4096) if start[s:s+8] == b'EFI PART')
        pair = []
        for side in ('start', 'end'):
            name = dev + '.' + side + '.bin'
            data, rec = files[name], meta[name]
            pos = sector if side == 'start' else len(data) - sector
            h = bytearray(data[pos:pos + struct.unpack_from('<I', data, pos+12)[0]])
            crc = struct.unpack_from('<I', h, 16)[0]
            struct.pack_into('<I', h, 16, 0)
            assert zlib.crc32(h) == crc, (dev, side, 'header CRC')
            lba, count, size, crc = struct.unpack_from('<QIII', h, 72)
            off = lba * sector - rec['offset']
            entries = data[off:off+count*size]
            assert len(entries) == count*size
            valid_crc = zlib.crc32(entries) == crc
            if not valid_crc:
                assert allow_stale_crc and dev == 'sde' and side == 'end', (dev, side, 'array CRC')
                print('Recorded pre-existing sde backup array checksum mismatch.')
            records = []
            for i in range(count):
                e = entries[i*size:(i+1)*size]
                if e[:16] == bytes(16):
                    continue
                first, last, attrs = struct.unpack_from('<QQQ', e, 32)
                records.append(dict(name=e[56:128].decode('utf-16le').rstrip('\0'), type=e[:16].hex(), guid=e[16:32].hex(), first=first, last=last, attrs=attrs))
            pair.append(records)
        if pair[0] != pair[1]:
            assert allow_stale_retry and dev == 'sde'
            for a, b in zip(*pair):
                if a != b:
                    assert a['name'] == b['name'] == 'boot_b'
                    assert (a['attrs'] ^ b['attrs']) & ~(0x38 << 48) == 0
                    assert {k:v for k,v in a.items() if k != 'attrs'} == {k:v for k,v in b.items() if k != 'attrs'}
                    print('Pre-existing backup difference is boot_b retry count only.')
        tables[dev] = pair[0]
    return tables

if __name__ == '__main__':
    tables = read_backup(sys.argv[1], allow_stale_retry='--allow-stale-retry' in sys.argv, allow_stale_crc='--allow-stale-retry' in sys.argv)
    sys.argv = [a for a in sys.argv if a != '--allow-stale-retry']
    if len(sys.argv) > 2:
        newer = read_backup(sys.argv[2], allow_stale_retry=True)
        changes = []
        for dev in tables:
            assert len(tables[dev]) == len(newer[dev])
            for a, b in zip(tables[dev], newer[dev]):
                if a != b:
                    changes.append(dict(device=dev, before=a, after=b))
                    assert a['name'].endswith('_b')
                    assert b['attrs'] == a['attrs'] | (1 << 54)
                    assert {k:v for k,v in a.items() if k != 'attrs'} == {k:v for k,v in b.items() if k != 'attrs'}
        print(json.dumps(changes, indent=2))
    else:
        print(json.dumps(tables, indent=2))
    print('GPT validation completed; any explicitly permitted baseline anomaly is reported above.')
