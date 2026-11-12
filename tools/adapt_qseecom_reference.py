"""Resolve known 7.1 -> 6.18 conflicts in the isolated compile-only tree."""
from pathlib import Path
import re

root = Path('/var/tmp/aura-qseecom-6.18.2/linux')
assert root.is_dir()

def edit(name, transform):
    path = root / name
    old = path.read_text()
    new = transform(old)
    assert old != new, name
    path.write_text(new)

edit('Documentation/tee/index.rst', lambda s: s.replace('   qtee\n', '   qtee\n   qseecom\n', 1))

def scm(s):
    needle = '\tif (!qcom_scm_qseecom_machine_is_allowed()) {'
    assert s.count(needle) == 1
    return s.replace(needle, '\t/* Explicitly configured userspace interface; no TA is called here. */\n'
                     '\tret = qcom_scm_qseecom_tee_init(scm);\n'
                     '\tif (ret)\n\t\treturn ret;\n\n' + needle)
edit('drivers/firmware/qcom/qcom_scm.c', scm)

def mdt(s):
    pattern = r'static bool qcom_mdt_bins_are_split\(const struct firmware \*fw\)\n\{.*?\n\}\n'
    matches = list(re.finditer(pattern, s, re.S))
    assert len(matches) == 2 and matches[0].group() == matches[1].group()
    second = matches[1]
    s = s[:second.start()] + s[second.end():]
    # Promote before addition; the source adds two u32 values before widening.
    return s.replace('seg_end = phdrs[i].p_offset + phdrs[i].p_filesz;',
                     'seg_end = (u64)phdrs[i].p_offset + phdrs[i].p_filesz;')
edit('drivers/soc/qcom/mdt_loader.c', mdt)

edit('include/linux/soc/qcom/mdt_loader.h', lambda s: s.replace(
    'ssize_t qcom_mdt_get_size(const struct firmware *fw);',
    'ssize_t qcom_mdt_get_size(const struct firmware *fw);\n'
    'ssize_t qcom_mdt_get_image_size(const struct firmware *fw);\n'
    'ssize_t qcom_mdt_read_image(struct device *dev, const struct firmware *fw,\n'
    '\t\t\t    const char *fw_name, void *mem, size_t mem_size);', 1))

def core(s):
    s, count = re.subn(r'kzalloc_obj\((\*\w+)\)', r'kzalloc(sizeof(\1), GFP_KERNEL)', s)
    assert count > 0
    return s
edit('drivers/tee/qseecom/core.c', core)
print('Resolved reference conflicts; API compilation still required.')
