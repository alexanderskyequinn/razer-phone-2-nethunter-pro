"""Initialize sensors before advertising the D-Bus name (SSC discovery reenters GLib)."""
import difflib
import tarfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
relative='src/iio-sensor-proxy.c'
with tarfile.open(root/'sources/archives/iio-sensor-proxy_3.9.orig.tar.bz2') as archive:
    member=next(m for m in archive.getmembers() if m.name.endswith('/'+relative))
    original=archive.extractfile(member).read().decode()
boundary='''\tdata->connection = g_object_ref (connection);
}

static void
name_acquired_handler (GDBusConnection *connection,
\t\t       const gchar     *name,
\t\t       gpointer         user_data)
{
\tSensorData *data = user_data;
\tguint i;
'''
assert original.count(boundary)==1
updated=original.replace(boundary,'''\tdata->connection = g_object_ref (connection);

\t/* SSC synchronous discovery runs a nested main loop. Finish discovery
\t * before g_bus_own_name() publishes the well-known name, otherwise a
\t * client can cache HasAccelerometer=false and never claim the sensor.
\t * Availability notifications are sent only to clients with a claim.
\t */
''')
needle='''\tsend_dbus_event (data, PROP_ALL);
\tsend_dbus_event (data, PROP_ALL_COMPASS);
\treturn;

bail:'''
assert updated.count(needle)==1
updated=updated.replace(needle,'''\treturn;

bail:''')
needle='''static gboolean
setup_dbus (SensorData *data,'''
assert updated.count(needle)==1
updated=updated.replace(needle,'''static void
name_acquired_handler (GDBusConnection *connection,
                       const gchar     *name,
                       gpointer         user_data)
{
\tSensorData *data = user_data;

\tsend_dbus_event (data, PROP_ALL);
\tsend_dbus_event (data, PROP_ALL_COMPASS);
}

static gboolean
setup_dbus (SensorData *data,''')
path=root/'sources/iio-sensor-proxy/iio-sensor-proxy-3.9'/relative
assert path.read_text() in (original,updated)
path.write_text(updated)
patch=''.join(difflib.unified_diff(original.splitlines(True),updated.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative))
(root/'port/iio-sensor-proxy-ssc-startup.patch').write_text(patch)
print(patch)
