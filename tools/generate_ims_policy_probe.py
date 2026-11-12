"""Read documented IMS policy fields and blocking reasons; no setting writes."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
base=(root/'port/aura-ims-probe.c').read_text()
start=base.index('    {\n    AWAIT(qmi_device_allocate_client')
bind_end=base.index('    {\n    AWAIT(qmi_client_ims_get_ims_services_enabled_setting')
text=base[:start]
for service,queries in [('IMS',[(0x90,[(0x14,'network_service_mask',8),(0x16,'call_mode_preference',4),(0x19,'normal_registration',1),(0x1b,'sms_enabled',1)]),(0x8d,[(0x11,'allowed_rat_mask',8)]),(0x48,[(0x15,'ACS_priority',1),(0x16,'ISIM_priority',1),(0x17,'NV_priority',1),(0x18,'PCO_priority',1),(0x19,'policy_service_mask',8)])]),('IMSA',[(0x37,[(0x10,'wwan_block_reason_mask',22),(0x11,'wlan_block_reason_mask',22)])])]:
 if service == 'IMSA':
  queries = [(0x36, [(0x10,'active_on_primary_subscription',1),(0x11,'active_on_secondary_subscription',1),(0x12,'active_on_tertiary_subscription',1)])] + queries
 block=base[start:bind_end]
 if service=='IMSA':
  block=block.replace('QMI_SERVICE_IMS','QMI_SERVICE_IMSA').replace('QMI_CLIENT_IMS','QMI_CLIENT_IMSA').replace('QmiMessageImsBind','QmiMessageImsaBind').replace('qmi_message_ims_bind','qmi_message_imsa_bind').replace('qmi_client_ims_bind','qmi_client_imsa_bind')
 text+=block
 for msg,fields in queries:
  text+=f'''    {{
    g_autoptr(QmiMessage) req = qmi_message_new(QMI_SERVICE_{service}, qmi_client_get_cid(client), qmi_client_get_next_transaction_id(client), {msg});
    AWAIT(qmi_device_command_full(dev, req, NULL, 5, NULL, ready, NULL));
    g_autoptr(QmiMessage) reply = qmi_device_command_full_finish(dev, result, &error);
    CHECK(reply);
    guint16 length = 0;
    const guint8 *value = qmi_message_get_raw_tlv(reply, 2, &length);
    CHECK(value && length == 4);
    g_print("{service} GET 0x{msg:04x} result=%u error=%u\\n", value[0] | (value[1]<<8), value[2] | (value[3]<<8));
    if (!value[0] && !value[1]) {{
'''
  for tlv,name,size in fields:
   text+=f'''        value = qmi_message_get_raw_tlv(reply, {tlv}, &length);
        if (value && length == {size}) {{
            guint64 n=0;
            for (guint i=0; i<MIN(length,8); i++) n |= ((guint64)value[i]) << (8*i);
            g_print("{name}=0x%" G_GINT64_MODIFIER "x\\n", n);
        }} else g_print("{name}=absent-or-unexpected-length(%u)\\n", value ? length : 0);
'''
  text+='    }\n    }\n'
 text+='''    AWAIT(qmi_device_release_client(dev, client, QMI_DEVICE_RELEASE_CLIENT_FLAGS_RELEASE_CID, 5, NULL, ready, NULL));
    CHECK(qmi_device_release_client_finish(dev, result, &error));
    }
'''
text+='''    AWAIT(qmi_device_close_async(dev, 5, NULL, ready, NULL));
    CHECK(qmi_device_close_finish(dev, result, &error));
    g_clear_object(&result);
    return 0;
}
'''
(root/'port/aura-ims-policy-probe.c').write_text(text,newline='\n')
(root/'tools/build_ims_policy_probe.sh').write_text((root/'tools/build_ims_probe.sh').read_text().replace('aura-ims-probe','aura-ims-policy-probe'),newline='\n')
