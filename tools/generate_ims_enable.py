"""Build a narrow standard IMS settings utility, separate from status probe."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
probe=(root/'port/aura-ims-probe.c').read_text()
prefix=probe[:probe.index('    {\n    AWAIT(qmi_client_ims_get_ims_services_enabled_setting')]
prefix=prefix.replace('CHECK(argc == 2 && (strcmp(argv[1], "0") == 0 || strcmp(argv[1], "1") == 0));\n    binding = (guint)(argv[1][0] - \'0\');', 'CHECK(argc == 2 && (!strcmp(argv[1], "enable") || !strcmp(argv[1], "normal-off") || !strcmp(argv[1], "enable-hold")));')
prefix=prefix.replace('g_clear_error(&error);\n    } else g_print("ims bind: success\\n");', 'return 1;\n    } else g_print("ims bind: success\\n");')
prefix += '''    g_autoptr(QmiMessageImsSetImsServicesEnabledSettingInput) input = qmi_message_ims_set_ims_services_enabled_setting_input_new();
    gboolean enable = strcmp(argv[1], "normal-off") != 0;
    if (enable) CHECK(qmi_message_ims_set_ims_services_enabled_setting_input_set_ims_sms_service_enable(input, TRUE, &error));
    CHECK(qmi_message_ims_set_ims_services_enabled_setting_input_set_ims_service_enabled(input, enable, &error));
    AWAIT(qmi_client_ims_set_ims_services_enabled_setting(QMI_CLIENT_IMS(client), input, 10, NULL, ready, NULL));
    g_autoptr(QmiMessageImsSetImsServicesEnabledSettingOutput) output = qmi_client_ims_set_ims_services_enabled_setting_finish(QMI_CLIENT_IMS(client), result, &error);
    CHECK(output);
    CHECK(qmi_message_ims_set_ims_services_enabled_setting_output_get_result(output, &error));
    g_print("Standard IMS settings request accepted; registration must be checked separately.\\n");
    if (!strcmp(argv[1], "enable-hold")) {
        g_print("Holding requesting IMS client for 90 seconds.\\n");
        gint64 until = g_get_monotonic_time() + 90 * G_USEC_PER_SEC;
        while (g_get_monotonic_time() < until) {
            while (g_main_context_iteration(NULL, FALSE)) {}
            g_usleep(100000);
        }
    }
    AWAIT(qmi_device_release_client(dev, client, QMI_DEVICE_RELEASE_CLIENT_FLAGS_RELEASE_CID, 5, NULL, ready, NULL));
    CHECK(qmi_device_release_client_finish(dev, result, &error));
    }
    AWAIT(qmi_device_close_async(dev, 5, NULL, ready, NULL));
    CHECK(qmi_device_close_finish(dev, result, &error));
    g_clear_object(&result);
    return 0;
}
'''
prefix=prefix.replace('/* Diagnostic: per-client binding and read-only IMS status. No settings writes. */', '/* Standard IMS service/SMS enable on subscription 0. No carrier profile, identity, or band edits.\n * Original libqmi 1.38 getter baseline was incorrect; no claimed rollback to that state. */')
(root/'port/aura-ims-enable.c').write_text(prefix)
build=(root/'tools/build_ims_probe.sh').read_text().replace('aura-ims-probe','aura-ims-enable')
(root/'tools/build_ims_enable.sh').write_text(build, newline='\n')
