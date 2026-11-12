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
    g_autoptr(QmiMessage) req = qmi_message_new(QMI_SERVICE_IMS, qmi_client_get_cid(client), qmi_client_get_next_transaction_id(client), 144);
    AWAIT(qmi_device_command_full(dev, req, NULL, 5, NULL, ready, NULL));
    g_autoptr(QmiMessage) reply = qmi_device_command_full_finish(dev, result, &error);
    CHECK(reply);
    guint16 length = 0;
    const guint8 *value = qmi_message_get_raw_tlv(reply, 2, &length);
    CHECK(value && length == 4);
    g_print("IMS GET 0x0090 result=%u error=%u\n", value[0] | (value[1]<<8), value[2] | (value[3]<<8));
    if (!value[0] && !value[1]) {
        value = qmi_message_get_raw_tlv(reply, 20, &length);
        if (value && length == 8) {
            guint64 n=0;
            for (guint i=0; i<MIN(length,8); i++) n |= ((guint64)value[i]) << (8*i);
            g_print("network_service_mask=0x%" G_GINT64_MODIFIER "x\n", n);
        } else g_print("network_service_mask=absent-or-unexpected-length(%u)\n", value ? length : 0);
        value = qmi_message_get_raw_tlv(reply, 22, &length);
        if (value && length == 4) {
            guint64 n=0;
            for (guint i=0; i<MIN(length,8); i++) n |= ((guint64)value[i]) << (8*i);
            g_print("call_mode_preference=0x%" G_GINT64_MODIFIER "x\n", n);
        } else g_print("call_mode_preference=absent-or-unexpected-length(%u)\n", value ? length : 0);
        value = qmi_message_get_raw_tlv(reply, 25, &length);
        if (value && length == 1) {
            guint64 n=0;
            for (guint i=0; i<MIN(length,8); i++) n |= ((guint64)value[i]) << (8*i);
            g_print("normal_registration=0x%" G_GINT64_MODIFIER "x\n", n);
        } else g_print("normal_registration=absent-or-unexpected-length(%u)\n", value ? length : 0);
        value = qmi_message_get_raw_tlv(reply, 27, &length);
        if (value && length == 1) {
            guint64 n=0;
            for (guint i=0; i<MIN(length,8); i++) n |= ((guint64)value[i]) << (8*i);
            g_print("sms_enabled=0x%" G_GINT64_MODIFIER "x\n", n);
        } else g_print("sms_enabled=absent-or-unexpected-length(%u)\n", value ? length : 0);
    }
    }
    {
    g_autoptr(QmiMessage) req = qmi_message_new(QMI_SERVICE_IMS, qmi_client_get_cid(client), qmi_client_get_next_transaction_id(client), 141);
    AWAIT(qmi_device_command_full(dev, req, NULL, 5, NULL, ready, NULL));
    g_autoptr(QmiMessage) reply = qmi_device_command_full_finish(dev, result, &error);
    CHECK(reply);
    guint16 length = 0;
    const guint8 *value = qmi_message_get_raw_tlv(reply, 2, &length);
    CHECK(value && length == 4);
    g_print("IMS GET 0x008d result=%u error=%u\n", value[0] | (value[1]<<8), value[2] | (value[3]<<8));
    if (!value[0] && !value[1]) {
        value = qmi_message_get_raw_tlv(reply, 17, &length);
        if (value && length == 8) {
            guint64 n=0;
            for (guint i=0; i<MIN(length,8); i++) n |= ((guint64)value[i]) << (8*i);
            g_print("allowed_rat_mask=0x%" G_GINT64_MODIFIER "x\n", n);
        } else g_print("allowed_rat_mask=absent-or-unexpected-length(%u)\n", value ? length : 0);
    }
    }
    {
    g_autoptr(QmiMessage) req = qmi_message_new(QMI_SERVICE_IMS, qmi_client_get_cid(client), qmi_client_get_next_transaction_id(client), 72);
    AWAIT(qmi_device_command_full(dev, req, NULL, 5, NULL, ready, NULL));
    g_autoptr(QmiMessage) reply = qmi_device_command_full_finish(dev, result, &error);
    CHECK(reply);
    guint16 length = 0;
    const guint8 *value = qmi_message_get_raw_tlv(reply, 2, &length);
    CHECK(value && length == 4);
    g_print("IMS GET 0x0048 result=%u error=%u\n", value[0] | (value[1]<<8), value[2] | (value[3]<<8));
    if (!value[0] && !value[1]) {
        value = qmi_message_get_raw_tlv(reply, 21, &length);
        if (value && length == 1) {
            guint64 n=0;
            for (guint i=0; i<MIN(length,8); i++) n |= ((guint64)value[i]) << (8*i);
            g_print("ACS_priority=0x%" G_GINT64_MODIFIER "x\n", n);
        } else g_print("ACS_priority=absent-or-unexpected-length(%u)\n", value ? length : 0);
        value = qmi_message_get_raw_tlv(reply, 22, &length);
        if (value && length == 1) {
            guint64 n=0;
            for (guint i=0; i<MIN(length,8); i++) n |= ((guint64)value[i]) << (8*i);
            g_print("ISIM_priority=0x%" G_GINT64_MODIFIER "x\n", n);
        } else g_print("ISIM_priority=absent-or-unexpected-length(%u)\n", value ? length : 0);
        value = qmi_message_get_raw_tlv(reply, 23, &length);
        if (value && length == 1) {
            guint64 n=0;
            for (guint i=0; i<MIN(length,8); i++) n |= ((guint64)value[i]) << (8*i);
            g_print("NV_priority=0x%" G_GINT64_MODIFIER "x\n", n);
        } else g_print("NV_priority=absent-or-unexpected-length(%u)\n", value ? length : 0);
        value = qmi_message_get_raw_tlv(reply, 24, &length);
        if (value && length == 1) {
            guint64 n=0;
            for (guint i=0; i<MIN(length,8); i++) n |= ((guint64)value[i]) << (8*i);
            g_print("PCO_priority=0x%" G_GINT64_MODIFIER "x\n", n);
        } else g_print("PCO_priority=absent-or-unexpected-length(%u)\n", value ? length : 0);
        value = qmi_message_get_raw_tlv(reply, 25, &length);
        if (value && length == 8) {
            guint64 n=0;
            for (guint i=0; i<MIN(length,8); i++) n |= ((guint64)value[i]) << (8*i);
            g_print("policy_service_mask=0x%" G_GINT64_MODIFIER "x\n", n);
        } else g_print("policy_service_mask=absent-or-unexpected-length(%u)\n", value ? length : 0);
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
        g_print("ims bind: %s\n", error ? error->message : "no response");
        g_clear_error(&error);
    } else g_print("ims bind: success\n");
    {
    g_autoptr(QmiMessage) req = qmi_message_new(QMI_SERVICE_IMSA, qmi_client_get_cid(client), qmi_client_get_next_transaction_id(client), 54);
    AWAIT(qmi_device_command_full(dev, req, NULL, 5, NULL, ready, NULL));
    g_autoptr(QmiMessage) reply = qmi_device_command_full_finish(dev, result, &error);
    CHECK(reply);
    guint16 length = 0;
    const guint8 *value = qmi_message_get_raw_tlv(reply, 2, &length);
    CHECK(value && length == 4);
    g_print("IMSA GET 0x0036 result=%u error=%u\n", value[0] | (value[1]<<8), value[2] | (value[3]<<8));
    if (!value[0] && !value[1]) {
        value = qmi_message_get_raw_tlv(reply, 16, &length);
        if (value && length == 1) {
            guint64 n=0;
            for (guint i=0; i<MIN(length,8); i++) n |= ((guint64)value[i]) << (8*i);
            g_print("active_on_primary_subscription=0x%" G_GINT64_MODIFIER "x\n", n);
        } else g_print("active_on_primary_subscription=absent-or-unexpected-length(%u)\n", value ? length : 0);
        value = qmi_message_get_raw_tlv(reply, 17, &length);
        if (value && length == 1) {
            guint64 n=0;
            for (guint i=0; i<MIN(length,8); i++) n |= ((guint64)value[i]) << (8*i);
            g_print("active_on_secondary_subscription=0x%" G_GINT64_MODIFIER "x\n", n);
        } else g_print("active_on_secondary_subscription=absent-or-unexpected-length(%u)\n", value ? length : 0);
        value = qmi_message_get_raw_tlv(reply, 18, &length);
        if (value && length == 1) {
            guint64 n=0;
            for (guint i=0; i<MIN(length,8); i++) n |= ((guint64)value[i]) << (8*i);
            g_print("active_on_tertiary_subscription=0x%" G_GINT64_MODIFIER "x\n", n);
        } else g_print("active_on_tertiary_subscription=absent-or-unexpected-length(%u)\n", value ? length : 0);
    }
    }
    {
    g_autoptr(QmiMessage) req = qmi_message_new(QMI_SERVICE_IMSA, qmi_client_get_cid(client), qmi_client_get_next_transaction_id(client), 55);
    AWAIT(qmi_device_command_full(dev, req, NULL, 5, NULL, ready, NULL));
    g_autoptr(QmiMessage) reply = qmi_device_command_full_finish(dev, result, &error);
    CHECK(reply);
    guint16 length = 0;
    const guint8 *value = qmi_message_get_raw_tlv(reply, 2, &length);
    CHECK(value && length == 4);
    g_print("IMSA GET 0x0037 result=%u error=%u\n", value[0] | (value[1]<<8), value[2] | (value[3]<<8));
    if (!value[0] && !value[1]) {
        value = qmi_message_get_raw_tlv(reply, 16, &length);
        if (value && length == 22) {
            guint64 n=0;
            for (guint i=0; i<MIN(length,8); i++) n |= ((guint64)value[i]) << (8*i);
            g_print("wwan_block_reason_mask=0x%" G_GINT64_MODIFIER "x\n", n);
        } else g_print("wwan_block_reason_mask=absent-or-unexpected-length(%u)\n", value ? length : 0);
        value = qmi_message_get_raw_tlv(reply, 17, &length);
        if (value && length == 22) {
            guint64 n=0;
            for (guint i=0; i<MIN(length,8); i++) n |= ((guint64)value[i]) << (8*i);
            g_print("wlan_block_reason_mask=0x%" G_GINT64_MODIFIER "x\n", n);
        } else g_print("wlan_block_reason_mask=absent-or-unexpected-length(%u)\n", value ? length : 0);
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
