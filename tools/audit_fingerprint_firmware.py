"""Check captured firmware layout without loading it or touching secure storage."""
import hashlib
import json
from pathlib import Path
import struct
import tarfile

project = Path(__file__).resolve().parents[1]
results = []
with tarfile.open(project / 'device-data/native-prerequisites/vendor-firmware.tar') as archive:
    for stem in ('firmware/fpctzappfingerprint', 'firmware_mnt/image/cmnlib'):
        mdt = archive.extractfile(stem + '.mdt').read()
        assert mdt[:6] == b'\x7fELF\x01\x01', 'Expected 32-bit little-endian ELF'
        hdr = struct.unpack_from('<16sHHIIIIIHHHHHH', mdt)
        phoff, phsize, phnum = hdr[5], hdr[9], hdr[10]
        assert phsize == 32 and phoff + phsize * phnum <= len(mdt)
        stock, candidate = bytearray(mdt), bytearray(mdt)
        segments = []
        for index in range(phnum):
            ph = struct.unpack_from('<8I', mdt, phoff + index * phsize)
            data = archive.extractfile(stem + f'.b{index:02d}').read()
            # Stock loads every file; the reference selects nonempty p_filesz.
            stock.extend(data)
            assert len(data) == ph[4], f'{stem}: segment {index} length mismatch'
            if ph[4]:
                candidate.extend(data)
            segments.append({'index': index, 'bytes': len(data), 'offset': ph[1]})
        assert candidate == stock
        results.append({'name': stem, 'class': 32, 'mdt_bytes': len(mdt),
                        'assembled_bytes': len(stock), 'segments': segments,
                        'sha256': hashlib.sha256(stock).hexdigest(),
                        'stock_and_candidate_layout_match': True})

out = project / 'build/kali/fingerprint/firmware-layout-audit.json'
out.write_text(json.dumps(results, indent=2) + '\n')
for result in results:
    print(f'{result["name"]}: {result["assembled_bytes"]} bytes, stock layout matches')
