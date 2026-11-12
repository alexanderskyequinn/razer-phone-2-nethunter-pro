"""Adapt the port's lens skeleton to the retained LC898217XC module data."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'port/aura-focus/bu64753.c').read_text()
s=s.replace('bu64753','lc898217').replace('BU64753','LC898217XC').replace('rohm,lc898217','onnn,lc898217xc')
s=s.replace('Razer RC2 main lens', 'Razer RC2 telephoto lens')
s=s.replace('Stock tuned initial 50 + 150 steps * 5 codes = 800.', 'Stock tuned initial 60 + 110 steps * 5 codes = 610.')
s=s.replace('#define FOCUS_MIN 50','#define FOCUS_MIN 60').replace('#define FOCUS_MAX 800','#define FOCUS_MAX 610').replace('CCI_REG16(0x45)','CCI_REG16(0x84)')
start=s.index('static const struct cci_reg_sequence settings[]')
end=s.index('static struct lc898217 *to_lens',start)
s=s[:start]+s[end:]
start=s.index('    usleep_range(1000, 1500);',s.index('static int lc898217_resume'))
end=s.index('    ret = cci_write(lens->map, FOCUS_REG',start)
s=s[:start]+'''    /* Stock power-on wait8ms; poll ID0xf0=0x72, then initialize ROM servo. */
    msleep(8);
    ret = cci_read(lens->map, CCI_REG8(0xf0), &status, NULL);
    if (ret) goto off;
    if (status != 0x72) { ret = -ENODEV; goto off; }
    ret = cci_write(lens->map, CCI_REG8(0xe0), 1, NULL);
    if (ret) goto off;
    for (tries = 0; tries < 100; ++tries) {
        ret = cci_read(lens->map, CCI_REG8(0xe3), &status, NULL);
        if (ret) goto off;
        if (status == 0) break;
        usleep_range(1000, 1500);
    }
    if (tries == 100) { ret = -ETIMEDOUT; goto off; }
''' + s[end:]
out=root/'port/aura-telefocus'
out.mkdir(exist_ok=True)
(out/'lc898217.c').write_text(s)
(out/'Makefile').write_text('obj-m += lc898217.o\n')
print(out/'lc898217.c')
