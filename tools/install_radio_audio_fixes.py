"""Install narrow Razer radio/audio compatibility changes in the pinned kernel."""
import difflib, subprocess, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1])
patch=[]
for name in ('drivers/bluetooth/hci_qca.c','drivers/bluetooth/btqca.c','sound/soc/qcom/sdm845.c'):
    original=subprocess.check_output(['git','-C',str(source),'show','HEAD:'+name],text=True)
    previous=original
    previous_sleep=original
    previous_audio=original
    if name.endswith('hci_qca.c'):
        needle='\thci_set_quirk(hdev, HCI_QUIRK_SIMULTANEOUS_DISCOVERY);'
        replacement=needle+'''

\t/* RC2 stock firmware crashes on LE extended scanning (opcode 0x2041). */
\tif (of_machine_is_compatible("razer,aura"))
\t\thci_set_quirk(hdev, HCI_QUIRK_BROKEN_EXT_SCAN);'''
        assert original.count(needle)==1
        updated=original.replace(needle,replacement)
        previous=updated
        needle='\t\tclear_bit(QCA_IBS_DISABLED, &qca->flags);\n\t\tqca_debugfs_init(hdev);'
        replacement='''\t\t/* Temporary RC2 diagnostic: keep host and controller sleep disabled. */
\t\tif (!of_machine_is_compatible("razer,aura"))
\t\t\tclear_bit(QCA_IBS_DISABLED, &qca->flags);
\t\tqca_debugfs_init(hdev);'''
        assert updated.count(needle)==1
        updated=updated.replace(needle,replacement)
        previous_sleep=updated
        # Sleep-disabled testing showed legacy scan is rejected by this firmware.
        # Retest extended scanning now that the UART sleep handshake is disabled.
        updated=updated.replace('''

\t/* RC2 stock firmware crashes on LE extended scanning (opcode 0x2041). */
\tif (of_machine_is_compatible("razer,aura"))
\t\thci_set_quirk(hdev, HCI_QUIRK_BROKEN_EXT_SCAN);''','')
    elif name.endswith('btqca.c'):
        updated=original.replace('#include <linux/module.h>', '#include <linux/module.h>\n#include <linux/of.h>')
        for mask in ('0x80', '0x01'):
            needle='\t\t\t\ttlv_nvm->data[0] |= '+mask+';'
            replacement='''\t\t\t\t/* Temporary RC2 sleep-handshake diagnostic. */
\t\t\t\tif (of_machine_is_compatible("razer,aura"))
\t\t\t\t\ttlv_nvm->data[0] &= ~'''+mask+''';
\t\t\t\telse
\t\t\t\t\ttlv_nvm->data[0] |= '''+mask+';'
            assert updated.count(needle)==1
            updated=updated.replace(needle,replacement)

    else:
        needle='''\t\t\tMI2S_BCLK_RATE, SNDRV_PCM_STREAM_PLAYBACK);
\t\tsnd_soc_dai_set_fmt(cpu_dai, fmt);
\t\tsnd_soc_dai_set_fmt(codec_dai, codec_dai_fmt);'''
        replacement='''\t\t\tMI2S_BCLK_RATE, SNDRV_PCM_STREAM_PLAYBACK);
\t\tsnd_soc_dai_set_fmt(cpu_dai, fmt);
\t\tfor_each_rtd_codec_dais(rtd, j, codec_dai)
\t\t\tsnd_soc_dai_set_fmt(codec_dai, codec_dai_fmt);'''
        assert original.count(needle)==1
        updated=original.replace(needle,replacement)
        if name.endswith('sdm845.c'):
            previous=updated
            updated=updated.replace('#include <linux/module.h>', '#include <linux/module.h>\n#include <linux/of.h>')
            needle='\n\t\t\tMI2S_BCLK_RATE, SNDRV_PCM_STREAM_PLAYBACK);'
            assert updated.count(needle)==1
            updated=updated.replace(needle, '\n\t\t\tof_machine_is_compatible("razer,aura") ? 3072000 : MI2S_BCLK_RATE,\n\t\t\tSNDRV_PCM_STREAM_PLAYBACK);')
            needle='\tsnd_mask_set_format(fmt, SNDRV_PCM_FORMAT_S16_LE);'
            replacement='''\tif (of_machine_is_compatible("razer,aura") &&
\t    snd_soc_rtd_to_cpu(rtd, 0)->id == QUATERNARY_MI2S_RX) {
\t\t/* RC2 stock TFA9912 profiles use 24-bit samples in 32-bit slots. */
\t\tsnd_mask_none(fmt);
\t\tsnd_mask_set_format(fmt, SNDRV_PCM_FORMAT_S24_LE);
\t} else {
\t\tsnd_mask_set_format(fmt, SNDRV_PCM_FORMAT_S16_LE);
\t}'''
            assert updated.count(needle)==1
            updated=updated.replace(needle,replacement)
            previous_audio=updated
            needle='\tcase QUATERNARY_MI2S_RX:\n\t\tcodec_dai_fmt |='
            replacement='''\tcase QUATERNARY_MI2S_RX:
\t\tif (of_machine_is_compatible("razer,aura"))
\t\t\tsnd_soc_dai_set_sysclk(cpu_dai,
\t\t\t\tQ6AFE_LPASS_CLK_ID_QUAD_MI2S_IBIT, 0,
\t\t\t\tSNDRV_PCM_STREAM_PLAYBACK);
\t\tcodec_dai_fmt |='''
            assert updated.count(needle)==1
            updated=updated.replace(needle,replacement)
            needle='\tcase SLIMBUS_0_RX...SLIMBUS_6_TX:\n\tcase QUATERNARY_MI2S_RX:\n\t\tbreak;'
            replacement='''\tcase QUATERNARY_MI2S_RX:
\t\tif (of_machine_is_compatible("razer,aura"))
\t\t\tsnd_soc_dai_set_sysclk(cpu_dai,
\t\t\t\tQ6AFE_LPASS_CLK_ID_QUAD_MI2S_IBIT, 0,
\t\t\t\tSNDRV_PCM_STREAM_PLAYBACK);
\t\tbreak;
\tcase SLIMBUS_0_RX...SLIMBUS_6_TX:
\t\tbreak;'''
            assert updated.count(needle)==1
            updated=updated.replace(needle,replacement)
    path=source/name
    assert path.read_text() in (original,previous,previous_sleep,previous_audio,updated),name+' has unexpected changes'
    path.write_text(updated)
    patch.extend(difflib.unified_diff(original.splitlines(True),updated.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(root/'port/razer-radio-audio-compatibility.patch').write_text(''.join(patch))
print('Installed Razer Bluetooth scan/sleep diagnostics and multi-amplifier MI2S format setup.')
