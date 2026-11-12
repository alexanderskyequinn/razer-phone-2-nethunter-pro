"""Read IMS registration and PDP failure state; never read subscriber URIs."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
probe=(root/'port/aura-ims-probe.c').read_text()
text=probe[:probe.index('    {\n    AWAIT(qmi_client_ims_get_ims_services_enabled_setting')]
text=text.replace('QMI_SERVICE_IMS','QMI_SERVICE_IMSA').replace('QMI_CLIENT_IMS','QMI_CLIENT_IMSA').replace('QmiMessageImsBind','QmiMessageImsaBind').replace('qmi_message_ims_bind','qmi_message_imsa_bind').replace('qmi_client_ims_bind','qmi_client_imsa_bind')
for msg,fields in [(0x20,[(0x10,'registered_bool'),(0x11,'registration_error'),(0x12,'registration_state')]),(0x28,[(0x10,'ims_pdp_connected'),(0x11,'pdp_failure_error'),(0x13,'pdp_failure_network')]),(0x2a,[(0x10,'operator_reserved_pco')])]:
    text+=f'''    {{
    g_autoptr(QmiMessage) req = qmi_message_new(QMI_SERVICE_IMSA, qmi_client_get_cid(client), qmi_client_get_next_transaction_id(client), {msg});
    AWAIT(qmi_device_command_full(dev, req, NULL, 5, NULL, ready, NULL));
    g_autoptr(QmiMessage) reply = qmi_device_command_full_finish(dev, result, &error);
    CHECK(reply);
    guint16 length = 0;
    const guint8 *value = qmi_message_get_raw_tlv(reply, 2, &length);
    CHECK(value && length == 4);
    g_print("IMSA GET 0x{msg:04x} result=%u error=%u\\n", value[0] | (value[1]<<8), value[2] | (value[3]<<8));
    if (!value[0] && !value[1]) {{
'''
    for tlv,name in fields:
        text+=f'''        value = qmi_message_get_raw_tlv(reply, {tlv}, &length);
        if (value && (length == 1 || length == 2 || length == 4)) {{
            guint32 n = 0;
            for (guint i=0; i<length; i++) n |= ((guint32)value[i]) << (i*8);
            g_print("{name}=%u\\n", n);
        }} else g_print("{name}=absent\\n");
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
(root/'port/aura-imsa-pdp-probe.c').write_text(text,newline='\n')
(root/'tools/build_imsa_pdp_probe.sh').write_text((root/'tools/build_ims_probe.sh').read_text().replace('aura-ims-probe','aura-imsa-pdp-probe'),newline='\n')
