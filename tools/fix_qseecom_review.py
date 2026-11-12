"""Follow-up fixes found while reviewing the 6.18 integration."""
from pathlib import Path

path = Path('/var/tmp/aura-qseecom-6.18.2/linux/drivers/tee/qseecom/core.c')
s = path.read_text()
start = s.index('static int qseecom_tee_open_session(')
end = s.index('static int qseecom_tee_close_session(', start)
part = s[start:end]
needle = '\tapp_id = qseecom_tee_app_get(ctxdata->qtee, app_name, &app_gen);'
assert needle in part
part = part.replace(needle, '\t/* Wait for concurrent loads to publish their owned registry entry. */\n'
                    '\tguard(mutex)(&ctxdata->qtee->load_lock);\n' + needle)
s = s[:start] + part + s[end:]
old = '''	if (!tee_shm_get_from_id(ctx, tee_shm_get_id(shm))) {
		kfree(listener);
		return -EINVAL;
	}'''
new = '''	{
		struct tee_shm *held = tee_shm_get_from_id(ctx, tee_shm_get_id(shm));

		if (IS_ERR(held)) {
			kfree(listener);
			return PTR_ERR(held);
		}
	}'''
assert old in s
s = s.replace(old, new, 1)
path.write_text(s)
print('Serialized lookup against load; corrected shared-memory error-pointer handling.')
