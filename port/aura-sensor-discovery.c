/* Read-only SSC SUID discovery. Wire schema: libssc 0.4.4 protobuf definitions.
 * Requests identifiers only; does not enable sensors or write their registry. */
#include <libqmi-glib.h>
#include <libqrtr-glib.h>
#include <string.h>

static GAsyncResult *result;
static guint reports;
static guint8 uids[128][18];
static guint uid_count;
static void ready(GObject *source, GAsyncResult *res, gpointer data)
{ (void)source; (void)data; result=g_object_ref(res); }
#define AWAIT(call) do { g_clear_object(&result); call; while (!result) g_main_context_iteration(NULL, TRUE); } while (0)
#define CHECK(expr) do { if (!(expr)) { g_printerr("%s: %s\n", #expr, error ? error->message : "invalid response"); return 1; } } while (0)

/* Bounds-checked protobuf field walker; ignore fields outside this schema. */
static gboolean varint(const guint8 **p, const guint8 *end, guint64 *value)
{
    *value=0;
    for (guint shift=0; shift<64 && *p<end; shift+=7) {
        guint8 b=*(*p)++;
        if (shift==63 && (b & 0xfe)) return FALSE;
        *value |= ((guint64)(b & 127)) << shift;
        if (!(b & 128)) return TRUE;
    }
    return FALSE;
}
static gboolean field(const guint8 **p, const guint8 *end, guint *number,
                      guint *wire, const guint8 **data, gsize *length)
{
    guint64 key,n;
    if (!varint(p,end,&key) || !(key>>3) || (key>>3)>G_MAXUINT) return FALSE;
    *number=key>>3; *wire=key&7; *data=*p;
    switch (*wire) {
    case 0: if (!varint(p,end,&n)) return FALSE; *length=*p-*data; return TRUE;
    case 1: n=8; break;
    case 2: if (!varint(p,end,&n)) return FALSE; *data=*p; break;
    case 5: n=4; break;
    default: return FALSE;
    }
    if (n>(guint64)(end-*p)) return FALSE;
    *length=n; *p+=n; return TRUE;
}
static void suid_report(const guint8 *p, gsize size)
{
    const guint8 *end=p+size,*data;
    guint number,wire,count=0; gsize length;
    g_autofree gchar *type=NULL;
    while (p<end) {
        if (!field(&p,end,&number,&wire,&data,&length)) return;
        if (number==1 && wire==2 && length<=128) {
            g_free(type); type=g_strndup((const gchar*)data,length);
        }
        if (number==2 && wire==2) {
            count++;
            if (length==18 && data[0]==9 && data[9]==17 && uid_count<128) {
                gboolean found=FALSE;
                for (guint i=0;i<uid_count;i++) if (!memcmp(uids[i],data,18)) found=TRUE;
                if (!found) memcpy(uids[uid_count++],data,18);
            }
        }
    }
    if (type && g_utf8_validate(type,-1,NULL)) {
        g_print("sensor-type=%s count=%u\n",type,count); reports++;
    }
}
static void attr_strings(const guint8 *p,gsize size,guint depth)
{
    const guint8 *end=p+size,*data; guint number,wire; gsize length;
    while(p<end) {
        if(!field(&p,end,&number,&wire,&data,&length)) return;
        if(depth==0 && number==1 && wire==2) attr_strings(data,length,1);
        if(depth==1 && number==2 && wire==2 && length<=128) {
            g_autofree gchar *s=g_strndup((const gchar*)data,length);
            if(g_utf8_validate(s,-1,NULL)) g_print(" %s",s);
        }
    }
}
static void attributes(const guint8 *p,gsize size)
{
    const guint8 *end=p+size,*data; guint number,wire; gsize length;
    g_print("ATTRIBUTES");
    while(p<end) {
        if(!field(&p,end,&number,&wire,&data,&length)) break;
        if(number!=1 || wire!=2) continue;
        const guint8 *q=data,*stop=data+length,*v,*values=NULL;
        guint n,w; gsize l,values_len=0; guint64 id=G_MAXUINT64;
        while(q<stop) {
            if(!field(&q,stop,&n,&w,&v,&l)) break;
            if(n==1 && w==0) { const guint8 *z=v; if(!varint(&z,v+l,&id)) break; }
            if(n==2 && w==2) {values=v;values_len=l;}
        }
        if(id<=2 && values) {g_print(" [%" G_GUINT64_FORMAT "]",id);attr_strings(values,values_len,0);}
    }
    g_print("\n");
}
static void report_body(const guint8 *p, gsize size)
{
    const guint8 *end=p+size,*data,*payload=NULL;
    guint number,wire,id=0; gsize length,payload_size=0;
    while (p<end) {
        if (!field(&p,end,&number,&wire,&data,&length)) return;
        if (number==1 && wire==5) id=data[0]|data[1]<<8|data[2]<<16|((guint32)data[3]<<24);
        if (number==3 && wire==2) { payload=data; payload_size=length; }
    }
    if (id==768 && payload) suid_report(payload,payload_size);
    if (id==128 && payload) attributes(payload,payload_size);
}
static void report(GArray *array)
{
    const guint8 *p=(const guint8*)array->data,*end=p+array->len,*data;
    guint number,wire; gsize length;
    while (p<end) {
        if (!field(&p,end,&number,&wire,&data,&length)) return;
        if (number==2 && wire==2) report_body(data,length);
    }
}
static void large(QmiClientSsc *client,QmiIndicationSscReportLargeOutput *out,gpointer data)
{ (void)client;(void)data; GArray *a=NULL; if(qmi_indication_ssc_report_large_output_get_data(out,&a,NULL)) report(a); }
static void small(QmiClientSsc *client,QmiIndicationSscReportSmallOutput *out,gpointer data)
{ (void)client;(void)data; GArray *a=NULL; if(qmi_indication_ssc_report_small_output_get_data(out,&a,NULL)) report(a); }

int main(void)
{
    g_autoptr(GError) error=NULL;
    g_autofree gchar *compat=NULL; gsize size=0;
    CHECK(g_file_get_contents("/proc/device-tree/compatible",&compat,&size,&error));
    CHECK(size>=sizeof("razer,aura") && !strcmp(compat,"razer,aura"));
    AWAIT(qrtr_bus_new(1000,NULL,ready,NULL));
    g_autoptr(QrtrBus) bus=qrtr_bus_new_finish(result,&error); CHECK(bus);
    QrtrNode *node=NULL;
    for(GList *l=qrtr_bus_peek_nodes(bus);l;l=l->next)
        if(qrtr_node_lookup_port(l->data,QMI_SERVICE_SSC)>=0) { node=l->data; break; }
    CHECK(node);
    AWAIT(qmi_device_new_from_node(node,NULL,ready,NULL));
    g_autoptr(QmiDevice) dev=qmi_device_new_from_node_finish(result,&error); CHECK(dev);
    AWAIT(qmi_device_open(dev,QMI_DEVICE_OPEN_FLAGS_NONE,5,NULL,ready,NULL));
    CHECK(qmi_device_open_finish(dev,result,&error));
    AWAIT(qmi_device_allocate_client(dev,QMI_SERVICE_SSC,QMI_CID_NONE,5,NULL,ready,NULL));
    g_autoptr(QmiClient) client=qmi_device_allocate_client_finish(dev,result,&error); CHECK(client);
    g_signal_connect(client,"report-large",G_CALLBACK(large),NULL);
    g_signal_connect(client,"report-small",G_CALLBACK(small),NULL);
    const gchar *types[]={"registry","accel","ambient_light","proximity",""};
    for(guint defaults=0;defaults<2;defaults++) for(guint t=0;t<G_N_ELEMENTS(types);t++) {
        guint8 payload[128]={0x0a}; guint n=strlen(types[t]); payload[1]=n;
        memcpy(payload+2,types[t],n);
        payload[n+2]=0x10; payload[n+3]=0; payload[n+4]=0x18; payload[n+5]=defaults;
        guint plen=n+6;
        guint8 frame[192]={0x0a,0x12,0x09};
        memset(frame+3,0xab,8); frame[11]=0x11; memset(frame+12,0xab,8);
        const guint8 tail[]={0x15,0x00,0x02,0x00,0x00,0x1a,0x04,0x08,0x01,0x10,0x00,0x22};
        memcpy(frame+20,tail,sizeof tail);
        frame[32]=plen+2; frame[33]=0x12; frame[34]=plen; memcpy(frame+35,payload,plen);
        g_autoptr(GArray) buf=g_array_new(FALSE,FALSE,1); g_array_append_vals(buf,frame,35+plen);
        g_autoptr(QmiMessageSscControlInput) input=qmi_message_ssc_control_input_new();
        CHECK(qmi_message_ssc_control_input_set_report_type(input,QMI_SSC_REPORT_TYPE_LARGE,&error));
        CHECK(qmi_message_ssc_control_input_set_data(input,buf,&error));
        g_print("DISCOVER type=%s defaults-only=%u\n",*types[t]?types[t]:"ALL",defaults);
        guint before=reports;
        AWAIT(qmi_client_ssc_control(QMI_CLIENT_SSC(client),input,5,NULL,ready,NULL));
        g_autoptr(QmiMessageSscControlOutput) out=qmi_client_ssc_control_finish(QMI_CLIENT_SSC(client),result,&error);
        CHECK(out && qmi_message_ssc_control_output_get_result(out,&error));
        gint64 until=g_get_monotonic_time()+G_USEC_PER_SEC;
        while(g_get_monotonic_time()<until) { while(g_main_context_iteration(NULL,FALSE)) {} g_usleep(10000); }
        if(reports==before) g_print("No discovery report in observation window\n");
    }
    for(guint i=0;i<uid_count;i++) {
        guint8 frame[37]={0x0a,0x12}; memcpy(frame+2,uids[i],18);
        const guint8 tail[]={0x15,1,0,0,0,0x1a,4,8,1,0x10,0,0x22,4,0x12,2,0x10,0};
        memcpy(frame+20,tail,sizeof tail);
        g_autoptr(GArray) buf=g_array_new(FALSE,FALSE,1);g_array_append_vals(buf,frame,sizeof frame);
        g_autoptr(QmiMessageSscControlInput) input=qmi_message_ssc_control_input_new();
        CHECK(qmi_message_ssc_control_input_set_report_type(input,QMI_SSC_REPORT_TYPE_LARGE,&error));
        CHECK(qmi_message_ssc_control_input_set_data(input,buf,&error));
        AWAIT(qmi_client_ssc_control(QMI_CLIENT_SSC(client),input,5,NULL,ready,NULL));
        g_autoptr(QmiMessageSscControlOutput) out=qmi_client_ssc_control_finish(QMI_CLIENT_SSC(client),result,&error);
        CHECK(out && qmi_message_ssc_control_output_get_result(out,&error));
        gint64 until=g_get_monotonic_time()+100000;
        while(g_get_monotonic_time()<until) {while(g_main_context_iteration(NULL,FALSE)) {} g_usleep(1000);}
    }
    AWAIT(qmi_device_release_client(dev,client,QMI_DEVICE_RELEASE_CLIENT_FLAGS_RELEASE_CID,5,NULL,ready,NULL));
    CHECK(qmi_device_release_client_finish(dev,result,&error));
    AWAIT(qmi_device_close_async(dev,5,NULL,ready,NULL));
    CHECK(qmi_device_close_finish(dev,result,&error));
    g_clear_object(&result); return 0;
}
