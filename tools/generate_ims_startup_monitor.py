"""Bounded stock-style IMS event subscriptions; only reassert enabled registration."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=(root/'port/aura-ims-enable.c').read_text()
callback='''static void indication(QmiDevice *dev, QmiMessage *msg, gpointer data)
{
    (void)dev; (void)data;
    /* Log identifiers only, never subscriber URIs or protocol payloads. */
    g_print("Event service=%u message=0x%04x\\n", qmi_message_get_service(msg), qmi_message_get_message_id(msg));
}

'''
source=source.replace('int main(',callback+'int main(')
setup='''    g_signal_connect(dev, QMI_DEVICE_SIGNAL_INDICATION, G_CALLBACK(indication), NULL);
    AWAIT(qmi_device_allocate_client(dev, QMI_SERVICE_IMSA, QMI_CID_NONE, 5, NULL, ready, NULL));
    g_autoptr(QmiClient) imsa = qmi_device_allocate_client_finish(dev, result, &error);
    CHECK(imsa);
    g_autoptr(QmiMessageImsaBindInput) imsa_bind = qmi_message_imsa_bind_input_new();
    CHECK(qmi_message_imsa_bind_input_set_binding(imsa_bind, 0, &error));
    AWAIT(qmi_client_imsa_bind(QMI_CLIENT_IMSA(imsa), imsa_bind, 5, NULL, ready, NULL));
    g_autoptr(QmiMessageImsaBindOutput) imsa_bound = qmi_client_imsa_bind_finish(QMI_CLIENT_IMSA(imsa), result, &error);
    CHECK(imsa_bound && qmi_message_imsa_bind_output_get_result(imsa_bound, &error));
'''
def subscribe(service,client,msg,tlvs):
    return f'''    {{
    g_autoptr(QmiMessage) req = qmi_message_new(QMI_SERVICE_{service}, qmi_client_get_cid({client}), qmi_client_get_next_transaction_id({client}), {msg});
    const guint8 enabled=1;
'''+''.join(f'    CHECK(qmi_message_add_raw_tlv(req, {tlv}, &enabled, 1, &error));\n' for tlv in tlvs)+f'''    AWAIT(qmi_device_command_full(dev, req, NULL, 5, NULL, ready, NULL));
    g_autoptr(QmiMessage) reply = qmi_device_command_full_finish(dev, result, &error);
    CHECK(reply);
    guint16 length=0;
    const guint8 *value=qmi_message_get_raw_tlv(reply, 2, &length);
    CHECK(value && length==4);
    g_print("{service} event subscription result=%u error=%u\\n", value[0]|value[1]<<8, value[2]|value[3]<<8);
    CHECK(!value[0] && !value[1]);
    }}
'''
source=source.replace('    {\n    AWAIT(qmi_device_allocate_client',setup+subscribe('IMSA','imsa',0x22,[0x10,0x11,0x13,0x16,0x17,0x1b])+'    {\n    AWAIT(qmi_device_allocate_client',1)
source=source.replace('    g_autoptr(QmiMessageImsSetImsServicesEnabledSettingInput)',subscribe('IMS','client',0x2a,[0x11,0x1f,0x2d,0x31])+'    g_autoptr(QmiMessageImsSetImsServicesEnabledSettingInput)',1)
source=source.replace('    if (enable) CHECK(qmi_message_ims_set_ims_services_enabled_setting_input_set_ims_sms_service_enable(input, TRUE, &error));','    CHECK(enable); /* Do not allow disable mode in this diagnostic. */')
source=source.replace('90 seconds','60 seconds').replace('90 * G_USEC_PER_SEC','60 * G_USEC_PER_SEC')
source=source.replace('    AWAIT(qmi_device_close_async', '''    AWAIT(qmi_device_release_client(dev, imsa, QMI_DEVICE_RELEASE_CLIENT_FLAGS_RELEASE_CID, 5, NULL, ready, NULL));
    CHECK(qmi_device_release_client_finish(dev, result, &error));
    AWAIT(qmi_device_close_async''')
(root/'port/aura-ims-startup-monitor.c').write_text(source,newline='\n')
(root/'tools/build_ims_startup_monitor.sh').write_text((root/'tools/build_ims_probe.sh').read_text().replace('aura-ims-probe','aura-ims-startup-monitor'),newline='\n')
