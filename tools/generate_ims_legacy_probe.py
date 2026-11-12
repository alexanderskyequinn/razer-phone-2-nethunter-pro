"""Query only documented legacy IMS registration/SMS/VoLTE enable flags.

Protocol reference: Qualcomm's ip_multimedia_subsystem_settings_v01.{h,c}
https://github.com/bcyj/android_tools_leeco_msm8996/tree/master/qmi/services
No subscriber strings, credentials or messages are emitted.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
probe=(root/'port/aura-ims-probe.c').read_text()
text=probe[:probe.index('    {\n    AWAIT(qmi_client_ims_get_ims_services_enabled_setting')]
for msg,fields in [(0x90,[(0x11,'volte_enabled'),(0x13,'ims_mobile_data_enabled'),(0x19,'ims_normal_registration_enabled'),(0x1b,'sms_over_ip_enabled'),(0x26,'carrier_config_enabled')]),(0x26,[(0x13,'legacy_ims_test_mode')]),(0x27,[(0x11,'legacy_sms_format'),(0x12,'legacy_sms_over_ip')]),(0x37,[(0x12,'legacy_mobile_data_enabled'),(0x13,'legacy_volte_enabled')])]:
    text+=f'''    {{
    g_autoptr(QmiMessage) req = qmi_message_new(QMI_SERVICE_IMS, qmi_client_get_cid(client), qmi_client_get_next_transaction_id(client), {msg});
    AWAIT(qmi_device_command_full(dev, req, NULL, 5, NULL, ready, NULL));
    g_autoptr(QmiMessage) reply = qmi_device_command_full_finish(dev, result, &error);
    CHECK(reply);
    guint16 length = 0;
    const guint8 *value = qmi_message_get_raw_tlv(reply, 2, &length);
    CHECK(value && length == 4);
    g_print("GET 0x{msg:04x} result=%u error=%u\\n", value[0] | (value[1]<<8), value[2] | (value[3]<<8));
    if (!value[0] && !value[1]) {{
'''
    for tlv,name in fields:
        text+=f'''        value = qmi_message_get_raw_tlv(reply, {tlv}, &length);
        if (value && length == 1) g_print("{name}=%u\\n", value[0]);
        else g_print("{name}=absent\\n");
'''
    text+='    }\n    }\n'
text+='''    AWAIT(qmi_device_release_client(dev, client, QMI_DEVICE_RELEASE_CLIENT_FLAGS_RELEASE_CID, 5, NULL, ready, NULL));
    CHECK(qmi_device_release_client_finish(dev, result, &error));
    }
    AWAIT(qmi_device_close_async(dev, 5, NULL, ready, NULL));
    CHECK(qmi_device_close_finish(dev, result, &error));
    g_clear_object(&result);
    return 0;
}
'''
(root/'port/aura-ims-legacy-probe.c').write_text(text, newline='\n')
(root/'tools/build_ims_legacy_probe.sh').write_text((root/'tools/build_ims_probe.sh').read_text().replace('aura-ims-probe','aura-ims-legacy-probe'), newline='\n')
