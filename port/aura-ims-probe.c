/* Diagnostic: per-client binding and read-only IMS status. No settings writes. */
#include <libqmi-glib.h>
#include <libqrtr-glib.h>
#include <string.h>

static GAsyncResult *result;
static void ready(GObject *source, GAsyncResult *res, gpointer user_data)
{
    (void)source; (void)user_data;
    result = g_object_ref(res);
}
#define AWAIT(call) do { g_clear_object(&result); call; \
    while (!result) g_main_context_iteration(NULL, TRUE); } while (0)
#define CHECK(expr) do { if (!(expr)) { \
    g_printerr("%s: %s\n", #expr, error ? error->message : "unexpected result"); \
    return 1; } } while (0)

int main(int argc, char **argv)
{
    g_autoptr(GError) error = NULL;
    g_autofree gchar *compat = NULL;
    gsize size = 0;
    CHECK(g_file_get_contents("/proc/device-tree/compatible", &compat, &size, &error));
    CHECK(size >= sizeof("razer,aura") && !strcmp(compat, "razer,aura"));

    AWAIT(qrtr_bus_new(1000, NULL, ready, NULL));
    g_autoptr(QrtrBus) bus = qrtr_bus_new_finish(result, &error);
    CHECK(bus);
    AWAIT(qrtr_bus_wait_for_node(bus, 0, 30000, NULL, ready, NULL));
    g_autoptr(QrtrNode) node = qrtr_bus_wait_for_node_finish(bus, result, &error);
    CHECK(node);
    /* Node 0 appears before its NAS server is advertised during cold boot. */
    guint binding = 0;
    CHECK(argc == 2 && (strcmp(argv[1], "0") == 0 || strcmp(argv[1], "1") == 0));
    binding = (guint)(argv[1][0] - '0');
    g_print("Client subscription binding=%u\n", binding);
    AWAIT(qmi_device_new_from_node(node, NULL, ready, NULL));
    g_autoptr(QmiDevice) dev = qmi_device_new_from_node_finish(result, &error);
    CHECK(dev);
    AWAIT(qmi_device_open(dev, QMI_DEVICE_OPEN_FLAGS_NONE, 5, NULL, ready, NULL));
    CHECK(qmi_device_open_finish(dev, result, &error));
    {
    AWAIT(qmi_device_allocate_client(dev, QMI_SERVICE_IMS, QMI_CID_NONE, 5, NULL, ready, NULL));
    g_autoptr(QmiClient) client = qmi_device_allocate_client_finish(dev, result, &error);
    CHECK(client);
    g_autoptr(QmiMessageImsBindInput) bind = qmi_message_ims_bind_input_new();
    CHECK(qmi_message_ims_bind_input_set_binding(bind, binding, &error));
    AWAIT(qmi_client_ims_bind(QMI_CLIENT_IMS(client), bind, 5, NULL, ready, NULL));
    g_autoptr(QmiMessageImsBindOutput) bound = qmi_client_ims_bind_finish(QMI_CLIENT_IMS(client), result, &error);
    if (!bound || !qmi_message_ims_bind_output_get_result(bound, &error)) {
        g_print("ims bind: %s\n", error ? error->message : "no response");
        g_clear_error(&error);
    } else g_print("ims bind: success\n");
    {
    AWAIT(qmi_client_ims_get_ims_services_enabled_setting(QMI_CLIENT_IMS(client), NULL, 5, NULL, ready, NULL));
    g_autoptr(QmiMessageImsGetImsServicesEnabledSettingOutput) out = qmi_client_ims_get_ims_services_enabled_setting_finish(QMI_CLIENT_IMS(client), result, &error);
    if (!out || !qmi_message_ims_get_ims_services_enabled_setting_output_get_result(out, &error)) {
        g_print("get_ims_services_enabled_setting: %s\n", error ? error->message : "no response");
        g_clear_error(&error);
    } else {
        { gboolean value;
          if (qmi_message_ims_get_ims_services_enabled_setting_output_get_ims_voice_service_enabled(out, &value, NULL))
              g_print("ims_voice_service_enabled=%u\n", (guint)value);
        }
        { gboolean value;
          if (qmi_message_ims_get_ims_services_enabled_setting_output_get_ims_registration_service_enabled(out, &value, NULL))
              g_print("ims_registration_service_enabled=%u\n", (guint)value);
        }
        { gboolean value;
          if (qmi_message_ims_get_ims_services_enabled_setting_output_get_ims_sms_service_enabled(out, &value, NULL))
              g_print("ims_sms_service_enabled=%u\n", (guint)value);
        }
    }
    }
    AWAIT(qmi_device_release_client(dev, client, QMI_DEVICE_RELEASE_CLIENT_FLAGS_RELEASE_CID, 5, NULL, ready, NULL));
    CHECK(qmi_device_release_client_finish(dev, result, &error));
    }
    {
    AWAIT(qmi_device_allocate_client(dev, QMI_SERVICE_IMSA, QMI_CID_NONE, 5, NULL, ready, NULL));
    g_autoptr(QmiClient) client = qmi_device_allocate_client_finish(dev, result, &error);
    CHECK(client);
    g_autoptr(QmiMessageImsaBindInput) bind = qmi_message_imsa_bind_input_new();
    CHECK(qmi_message_imsa_bind_input_set_binding(bind, binding, &error));
    AWAIT(qmi_client_imsa_bind(QMI_CLIENT_IMSA(client), bind, 5, NULL, ready, NULL));
    g_autoptr(QmiMessageImsaBindOutput) bound = qmi_client_imsa_bind_finish(QMI_CLIENT_IMSA(client), result, &error);
    if (!bound || !qmi_message_imsa_bind_output_get_result(bound, &error)) {
        g_print("imsa bind: %s\n", error ? error->message : "no response");
        g_clear_error(&error);
    } else g_print("imsa bind: success\n");
    {
    AWAIT(qmi_client_imsa_get_ims_registration_status(QMI_CLIENT_IMSA(client), NULL, 5, NULL, ready, NULL));
    g_autoptr(QmiMessageImsaGetImsRegistrationStatusOutput) out = qmi_client_imsa_get_ims_registration_status_finish(QMI_CLIENT_IMSA(client), result, &error);
    if (!out || !qmi_message_imsa_get_ims_registration_status_output_get_result(out, &error)) {
        g_print("get_ims_registration_status: %s\n", error ? error->message : "no response");
        g_clear_error(&error);
    } else {
        { QmiImsaImsRegistrationStatus value;
          if (qmi_message_imsa_get_ims_registration_status_output_get_ims_registration_status(out, &value, NULL))
              g_print("ims_registration_status=%u\n", (guint)value);
        }
        { guint16 value;
          if (qmi_message_imsa_get_ims_registration_status_output_get_ims_registration_error_code(out, &value, NULL))
              g_print("ims_registration_error_code=%u\n", (guint)value);
        }
        { QmiImsaRegistrationTechnology value;
          if (qmi_message_imsa_get_ims_registration_status_output_get_ims_registration_technology(out, &value, NULL))
              g_print("ims_registration_technology=%u\n", (guint)value);
        }
    }
    }
    {
    AWAIT(qmi_client_imsa_get_ims_services_status(QMI_CLIENT_IMSA(client), NULL, 5, NULL, ready, NULL));
    g_autoptr(QmiMessageImsaGetImsServicesStatusOutput) out = qmi_client_imsa_get_ims_services_status_finish(QMI_CLIENT_IMSA(client), result, &error);
    if (!out || !qmi_message_imsa_get_ims_services_status_output_get_result(out, &error)) {
        g_print("get_ims_services_status: %s\n", error ? error->message : "no response");
        g_clear_error(&error);
    } else {
        { QmiImsaServiceStatus value;
          if (qmi_message_imsa_get_ims_services_status_output_get_ims_voice_service_status(out, &value, NULL))
              g_print("ims_voice_service_status=%u\n", (guint)value);
        }
        { QmiImsaServiceStatus value;
          if (qmi_message_imsa_get_ims_services_status_output_get_ims_sms_service_status(out, &value, NULL))
              g_print("ims_sms_service_status=%u\n", (guint)value);
        }
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
