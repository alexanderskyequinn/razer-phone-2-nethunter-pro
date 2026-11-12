"""Historical comparison probe; binds own clients and reads status.

WARNING: libqmi 1.38 IMS registration/SMS setting getters use wrong TLV IDs.
Use aura-ims-legacy-probe's direct GET 0x90 fields for authoritative settings.
IMSA registration getters are independently verified against direct responses.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
base = (root/'port/aura-modem-data-mode.c').read_text()
prefix = base[:base.index('    g_autoptr(GArray) services')]
prefix = prefix.replace('int main(void)', 'int main(int argc, char **argv)')
prefix += '''    guint binding = 0;
    CHECK(argc == 2 && (strcmp(argv[1], "0") == 0 || strcmp(argv[1], "1") == 0));
    binding = (guint)(argv[1][0] - '0');
    g_print("Client subscription binding=%u\\n", binding);
    AWAIT(qmi_device_new_from_node(node, NULL, ready, NULL));
    g_autoptr(QmiDevice) dev = qmi_device_new_from_node_finish(result, &error);
    CHECK(dev);
    AWAIT(qmi_device_open(dev, QMI_DEVICE_OPEN_FLAGS_NONE, 5, NULL, ready, NULL));
    CHECK(qmi_device_open_finish(dev, result, &error));
'''
for svc,typ in [('ims','Ims'),('imsa','Imsa')]:
    prefix += f'''    {{
    AWAIT(qmi_device_allocate_client(dev, QMI_SERVICE_{svc.upper()}, QMI_CID_NONE, 5, NULL, ready, NULL));
    g_autoptr(QmiClient) client = qmi_device_allocate_client_finish(dev, result, &error);
    CHECK(client);
    g_autoptr(QmiMessage{typ}BindInput) bind = qmi_message_{svc}_bind_input_new();
    CHECK(qmi_message_{svc}_bind_input_set_binding(bind, binding, &error));
    AWAIT(qmi_client_{svc}_bind(QMI_CLIENT_{svc.upper()}(client), bind, 5, NULL, ready, NULL));
    g_autoptr(QmiMessage{typ}BindOutput) bound = qmi_client_{svc}_bind_finish(QMI_CLIENT_{svc.upper()}(client), result, &error);
    if (!bound || !qmi_message_{svc}_bind_output_get_result(bound, &error)) {{
        g_print("{svc} bind: %s\\n", error ? error->message : "no response");
        g_clear_error(&error);
    }} else g_print("{svc} bind: success\\n");
'''
    queries = [('get_ims_services_enabled_setting', 'GetImsServicesEnabledSetting', [('ims_voice_service_enabled','gboolean'), ('ims_registration_service_enabled','gboolean'), ('ims_sms_service_enabled','gboolean')])] if svc == 'ims' else [('get_ims_registration_status','GetImsRegistrationStatus',[('ims_registration_status','QmiImsaImsRegistrationStatus'),('ims_registration_error_code','guint16'),('ims_registration_technology','QmiImsaRegistrationTechnology')]),('get_ims_services_status','GetImsServicesStatus',[('ims_voice_service_status','QmiImsaServiceStatus'),('ims_sms_service_status','QmiImsaServiceStatus')])]
    for method,mt,fields in queries:
        prefix += f'''    {{
    AWAIT(qmi_client_{svc}_{method}(QMI_CLIENT_{svc.upper()}(client), NULL, 5, NULL, ready, NULL));
    g_autoptr(QmiMessage{typ}{mt}Output) out = qmi_client_{svc}_{method}_finish(QMI_CLIENT_{svc.upper()}(client), result, &error);
    if (!out || !qmi_message_{svc}_{method}_output_get_result(out, &error)) {{
        g_print("{method}: %s\\n", error ? error->message : "no response");
        g_clear_error(&error);
    }} else {{
'''
        for field,ctype in fields:
            prefix += f'''        {{ {ctype} value;
          if (qmi_message_{svc}_{method}_output_get_{field}(out, &value, NULL))
              g_print("{field}=%u\\n", (guint)value);
        }}
'''
        prefix += '    }\n    }\n'
    prefix += '''    AWAIT(qmi_device_release_client(dev, client, QMI_DEVICE_RELEASE_CLIENT_FLAGS_RELEASE_CID, 5, NULL, ready, NULL));
    CHECK(qmi_device_release_client_finish(dev, result, &error));
    }
'''
prefix += '''    AWAIT(qmi_device_close_async(dev, 5, NULL, ready, NULL));
    CHECK(qmi_device_close_finish(dev, result, &error));
    g_clear_object(&result);
    return 0;
}
'''
prefix = prefix[prefix.index('#include'):]
(root/'port/aura-ims-probe.c').write_text('/* Diagnostic: per-client binding and read-only IMS status. No settings writes. */\n'+prefix)
