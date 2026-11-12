/* Standard IMS service/SMS enable on subscription 0. No carrier profile, identity, or band edits.
 * Original libqmi 1.38 getter baseline was incorrect; no claimed rollback to that state. */
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

static void indication(QmiDevice *dev, QmiMessage *msg, gpointer data)
{
    (void)dev; (void)data;
    /* Log identifiers only, never subscriber URIs or protocol payloads. */
    g_print("Event service=%u message=0x%04x\n", qmi_message_get_service(msg), qmi_message_get_message_id(msg));
}

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
    CHECK(argc == 2 && (!strcmp(argv[1], "enable") || !strcmp(argv[1], "normal-off") || !strcmp(argv[1], "enable-hold")));
    g_print("Client subscription binding=%u\n", binding);
    AWAIT(qmi_device_new_from_node(node, NULL, ready, NULL));
    g_autoptr(QmiDevice) dev = qmi_device_new_from_node_finish(result, &error);
    CHECK(dev);
    AWAIT(qmi_device_open(dev, QMI_DEVICE_OPEN_FLAGS_NONE, 5, NULL, ready, NULL));
    CHECK(qmi_device_open_finish(dev, result, &error));
    g_signal_connect(dev, QMI_DEVICE_SIGNAL_INDICATION, G_CALLBACK(indication), NULL);
    AWAIT(qmi_device_allocate_client(dev, QMI_SERVICE_IMSA, QMI_CID_NONE, 5, NULL, ready, NULL));
    g_autoptr(QmiClient) imsa = qmi_device_allocate_client_finish(dev, result, &error);
    CHECK(imsa);
    g_autoptr(QmiMessageImsaBindInput) imsa_bind = qmi_message_imsa_bind_input_new();
    CHECK(qmi_message_imsa_bind_input_set_binding(imsa_bind, 0, &error));
    AWAIT(qmi_client_imsa_bind(QMI_CLIENT_IMSA(imsa), imsa_bind, 5, NULL, ready, NULL));
    g_autoptr(QmiMessageImsaBindOutput) imsa_bound = qmi_client_imsa_bind_finish(QMI_CLIENT_IMSA(imsa), result, &error);
    CHECK(imsa_bound && qmi_message_imsa_bind_output_get_result(imsa_bound, &error));
    {
    g_autoptr(QmiMessage) req = qmi_message_new(QMI_SERVICE_IMSA, qmi_client_get_cid(imsa), qmi_client_get_next_transaction_id(imsa), 34);
    const guint8 enabled=1;
    CHECK(qmi_message_add_raw_tlv(req, 16, &enabled, 1, &error));
    CHECK(qmi_message_add_raw_tlv(req, 17, &enabled, 1, &error));
    CHECK(qmi_message_add_raw_tlv(req, 19, &enabled, 1, &error));
    CHECK(qmi_message_add_raw_tlv(req, 22, &enabled, 1, &error));
    CHECK(qmi_message_add_raw_tlv(req, 23, &enabled, 1, &error));
    CHECK(qmi_message_add_raw_tlv(req, 27, &enabled, 1, &error));
    AWAIT(qmi_device_command_full(dev, req, NULL, 5, NULL, ready, NULL));
    g_autoptr(QmiMessage) reply = qmi_device_command_full_finish(dev, result, &error);
    CHECK(reply);
    guint16 length=0;
    const guint8 *value=qmi_message_get_raw_tlv(reply, 2, &length);
    CHECK(value && length==4);
    g_print("IMSA event subscription result=%u error=%u\n", value[0]|value[1]<<8, value[2]|value[3]<<8);
    CHECK(!value[0] && !value[1]);
    }
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
        return 1;
    } else g_print("ims bind: success\n");
    {
    g_autoptr(QmiMessage) req = qmi_message_new(QMI_SERVICE_IMS, qmi_client_get_cid(client), qmi_client_get_next_transaction_id(client), 42);
    const guint8 enabled=1;
    CHECK(qmi_message_add_raw_tlv(req, 17, &enabled, 1, &error));
    CHECK(qmi_message_add_raw_tlv(req, 31, &enabled, 1, &error));
    CHECK(qmi_message_add_raw_tlv(req, 45, &enabled, 1, &error));
    CHECK(qmi_message_add_raw_tlv(req, 49, &enabled, 1, &error));
    AWAIT(qmi_device_command_full(dev, req, NULL, 5, NULL, ready, NULL));
    g_autoptr(QmiMessage) reply = qmi_device_command_full_finish(dev, result, &error);
    CHECK(reply);
    guint16 length=0;
    const guint8 *value=qmi_message_get_raw_tlv(reply, 2, &length);
    CHECK(value && length==4);
    g_print("IMS event subscription result=%u error=%u\n", value[0]|value[1]<<8, value[2]|value[3]<<8);
    CHECK(!value[0] && !value[1]);
    }
    g_autoptr(QmiMessageImsSetImsServicesEnabledSettingInput) input = qmi_message_ims_set_ims_services_enabled_setting_input_new();
    gboolean enable = strcmp(argv[1], "normal-off") != 0;
    CHECK(enable); /* Do not allow disable mode in this diagnostic. */
    CHECK(qmi_message_ims_set_ims_services_enabled_setting_input_set_ims_service_enabled(input, enable, &error));
    AWAIT(qmi_client_ims_set_ims_services_enabled_setting(QMI_CLIENT_IMS(client), input, 10, NULL, ready, NULL));
    g_autoptr(QmiMessageImsSetImsServicesEnabledSettingOutput) output = qmi_client_ims_set_ims_services_enabled_setting_finish(QMI_CLIENT_IMS(client), result, &error);
    CHECK(output);
    CHECK(qmi_message_ims_set_ims_services_enabled_setting_output_get_result(output, &error));
    g_print("Standard IMS settings request accepted; registration must be checked separately.\n");
    if (!strcmp(argv[1], "enable-hold")) {
        g_print("Holding requesting IMS client for 60 seconds.\n");
        gint64 until = g_get_monotonic_time() + 60 * G_USEC_PER_SEC;
        while (g_get_monotonic_time() < until) {
            while (g_main_context_iteration(NULL, FALSE)) {}
            g_usleep(100000);
        }
    }
    AWAIT(qmi_device_release_client(dev, client, QMI_DEVICE_RELEASE_CLIENT_FLAGS_RELEASE_CID, 5, NULL, ready, NULL));
    CHECK(qmi_device_release_client_finish(dev, result, &error));
    }
    AWAIT(qmi_device_release_client(dev, imsa, QMI_DEVICE_RELEASE_CLIENT_FLAGS_RELEASE_CID, 5, NULL, ready, NULL));
    CHECK(qmi_device_release_client_finish(dev, result, &error));
    AWAIT(qmi_device_close_async(dev, 5, NULL, ready, NULL));
    CHECK(qmi_device_close_finish(dev, result, &error));
    g_clear_object(&result);
    return 0;
}
