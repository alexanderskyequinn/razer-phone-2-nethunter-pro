/* Apply only volatile NAS usage/domain preferences on the Razer aura.
 * No SIM, subscriber identity, band mask, carrier profile or NV file access.
 * libqmi 1.38 / libqrtr-glib 1.0 APIs. */
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

int main(void)
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
    g_autoptr(GArray) services = g_array_new(FALSE, FALSE, sizeof(guint32));
    guint32 nas_service = QMI_SERVICE_NAS;
    g_array_append_val(services, nas_service);
    AWAIT(qrtr_node_wait_for_services(node, services, 30000, NULL, ready, NULL));
    CHECK(qrtr_node_wait_for_services_finish(node, result, &error));
    AWAIT(qmi_device_new_from_node(node, NULL, ready, NULL));
    g_autoptr(QmiDevice) dev = qmi_device_new_from_node_finish(result, &error);
    CHECK(dev);
    AWAIT(qmi_device_open(dev, QMI_DEVICE_OPEN_FLAGS_NONE, 10, NULL, ready, NULL));
    CHECK(qmi_device_open_finish(dev, result, &error));
    AWAIT(qmi_device_allocate_client(dev, QMI_SERVICE_NAS, QMI_CID_NONE, 10, NULL, ready, NULL));
    g_autoptr(QmiClient) client = qmi_device_allocate_client_finish(dev, result, &error);
    CHECK(client);

    g_autoptr(QmiMessageNasSetSystemSelectionPreferenceInput) input =
        qmi_message_nas_set_system_selection_preference_input_new();
    CHECK(qmi_message_nas_set_system_selection_preference_input_set_change_duration(
        input, QMI_NAS_CHANGE_DURATION_POWER_CYCLE, &error));
    CHECK(qmi_message_nas_set_system_selection_preference_input_set_usage_preference(
        input, QMI_NAS_USAGE_PREFERENCE_DATA_CENTRIC, &error));
    CHECK(qmi_message_nas_set_system_selection_preference_input_set_service_domain_preference(
        input, QMI_NAS_SERVICE_DOMAIN_PREFERENCE_PS_ONLY, &error));
    AWAIT(qmi_client_nas_set_system_selection_preference(QMI_CLIENT_NAS(client), input, 10, NULL, ready, NULL));
    g_autoptr(QmiMessageNasSetSystemSelectionPreferenceOutput) output =
        qmi_client_nas_set_system_selection_preference_finish(QMI_CLIENT_NAS(client), result, &error);
    CHECK(output);
    CHECK(qmi_message_nas_set_system_selection_preference_output_get_result(output, &error));

    QmiNasUsagePreference usage = QMI_NAS_USAGE_PREFERENCE_UNKNOWN;
    QmiNasServiceDomainPreference domain = QMI_NAS_SERVICE_DOMAIN_PREFERENCE_CS_PS;
    /* The firmware may acknowledge SET before GET reflects the new values. */
    for (guint attempt = 0; attempt < 20; attempt++) {
        AWAIT(qmi_client_nas_get_system_selection_preference(QMI_CLIENT_NAS(client), NULL, 2, NULL, ready, NULL));
        g_autoptr(QmiMessageNasGetSystemSelectionPreferenceOutput) status =
            qmi_client_nas_get_system_selection_preference_finish(QMI_CLIENT_NAS(client), result, &error);
        CHECK(status);
        CHECK(qmi_message_nas_get_system_selection_preference_output_get_result(status, &error));
        CHECK(qmi_message_nas_get_system_selection_preference_output_get_usage_preference(status, &usage, &error));
        CHECK(qmi_message_nas_get_system_selection_preference_output_get_service_domain_preference(status, &domain, &error));
        if (usage == QMI_NAS_USAGE_PREFERENCE_DATA_CENTRIC &&
            domain == QMI_NAS_SERVICE_DOMAIN_PREFERENCE_PS_ONLY)
            break;
        g_usleep(250000);
    }
    CHECK(usage == QMI_NAS_USAGE_PREFERENCE_DATA_CENTRIC);
    CHECK(domain == QMI_NAS_SERVICE_DOMAIN_PREFERENCE_PS_ONLY);
    g_print("Verified volatile data-centric / packet-only NAS preferences.\n");

    AWAIT(qmi_device_release_client(dev, client, QMI_DEVICE_RELEASE_CLIENT_FLAGS_RELEASE_CID, 5, NULL, ready, NULL));
    CHECK(qmi_device_release_client_finish(dev, result, &error));
    AWAIT(qmi_device_close_async(dev, 5, NULL, ready, NULL));
    CHECK(qmi_device_close_finish(dev, result, &error));
    g_clear_object(&result);
    return 0;
}
