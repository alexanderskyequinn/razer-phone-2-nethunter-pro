"""Add aura's 32-bit shared library startup and fix reviewed lifetime races.

Operates only on the isolated experimental kernel. Run once after the base
reference adaptation, then export_qseecom_backport.py records the whole patch.
"""
from pathlib import Path

project = Path(__file__).resolve().parents[1]
root = Path('/var/tmp/aura-qseecom-6.18.2/linux')
scm_path = root / 'drivers/firmware/qcom/qcom_scm.c'
scm = scm_path.read_text()
marker = 'EXPORT_SYMBOL_GPL(qcom_scm_qseecom_app_load);\n'
assert 'int qcom_scm_qseecom_load_cmnlib(' not in scm
scm = scm.replace(marker, marker + '\n' + (project / 'port/aura-fingerprint/qseecom-cmnlib.inc').read_text(), 1)
scm_path.write_text(scm)

header_path = root / 'include/linux/firmware/qcom/qcom_scm.h'
header = header_path.read_text().replace('int qcom_scm_qseecom_app_shutdown(u32 app_id);',
    'int qcom_scm_qseecom_load_cmnlib(void *img, size_t mdt_len, size_t img_len);\n'
    'int qcom_scm_qseecom_app_shutdown(u32 app_id);', 1)
marker = 'static inline int qcom_scm_qseecom_app_shutdown(u32 app_id)'
header = header.replace(marker,
    'static inline int qcom_scm_qseecom_load_cmnlib(void *img, size_t mdt_len,\n'
    '\t\t\t\t\t     size_t img_len)\n{\n\treturn -EOPNOTSUPP;\n}\n\n' + marker, 1)
header_path.write_text(header)

path = root / 'drivers/tee/qseecom/core.c'
s = path.read_text().replace('#include <linux/errno.h>', '#include <linux/errno.h>\n#include <linux/elf.h>', 1)
s = s.replace(' * @apps_lock:', ' * @load_lock:   Serializes application loading and registry publication.\n * @apps_lock:', 1)
s = s.replace('\tstruct mutex apps_lock;', '\tstruct mutex load_lock;\n\tstruct mutex apps_lock;', 1)
s = s.replace('\tinit_waitqueue_head(&qtee->supp.wq);',
              '\tret = devm_mutex_init(dev, &qtee->load_lock);\n\tif (ret)\n\t\treturn ret;\n\n'
              '\tinit_waitqueue_head(&qtee->supp.wq);', 1)

# A session holds the app reference through the entire invocation.
start = s.index('static int qseecom_tee_invoke_func(')
end = s.index('\n/*\n * Listener services', start)
invoke = s[start:end]
invoke = invoke.replace('\tmutex_lock(&ctxdata->mutex);', '\tguard(mutex)(&ctxdata->mutex);', 1)
invoke = invoke.replace('\tmutex_unlock(&ctxdata->mutex);\n', '', 1)
s = s[:start] + invoke + s[end:]

# Failed session allocation must release a reference acquired during lookup.
start = s.index('static int qseecom_tee_open_session(')
end = s.index('static int qseecom_tee_close_session(', start)
opening = s[start:end]
needle = '\t\t\t\t      &arg->session);\n\tif (ret)\n\t\treturn ret;'
assert needle in opening
opening = opening.replace(needle, '\t\t\t\t      &arg->session);\n\tif (ret) {\n'
    '\t\tqseecom_tee_app_put(ctxdata->qtee, app_id, app_gen);\n\t\treturn ret;\n\t}', 1)
s = s[:start] + opening + s[end:]

# Reuse the checked staging path for both signed images.
start = s.index('static int qseecom_tee_supp_load_app(')
end = s.index('\n/*\n * Sessions on the privileged device', start)
old = s[start:end]
body_start = old.index('\tlen = qcom_mdt_get_image_size(mdt);')
body_end = old.index('\n\t/*\n\t * From here the application is live')
body = old[body_start:body_end]
body = body.replace('\telse\n\t\tret = qcom_scm_qseecom_app_load',
    '\telse if (service)\n\t\tret = qcom_scm_qseecom_load_cmnlib(aligned, mdt_len, img_len);\n'
    '\telse\n\t\tret = qcom_scm_qseecom_app_load', 1)
body = body.replace('&app_id);', 'app_id);')
body = body.replace('app_name, ret', 'name, ret')
helper = '''static int qseecom_tee_load_image(struct qseecom_tee *qtee,
				  const char *name, bool service, u32 *app_id)
{
	struct qcom_tzmem_pool_config pool_config = {
		.policy = QCOM_TZMEM_POLICY_STATIC,
	};
	char fw_name[QSEECOM_TEE_MAX_APP_NAME + sizeof(".mdt")];
	size_t img_len, mdt_len, stage_len;
	phys_addr_t stage_phys, img_phys;
	const struct firmware *mdt;
	struct qcom_tzmem_pool *pool;
	void *stage, *aligned;
	ssize_t len;
	int ret;

	snprintf(fw_name, sizeof(fw_name), "%s.mdt", name);
	ret = request_firmware(&mdt, fw_name, qtee->dev);
	if (ret)
		return ret;
	/* This backport's MDT assembler supports only little-endian ELF32. */
	if (mdt->size < sizeof(struct elf32_hdr) ||
	    mdt->data[EI_CLASS] != ELFCLASS32 ||
	    mdt->data[EI_DATA] != ELFDATA2LSB) {
		ret = -EOPNOTSUPP;
		goto out_release;
	}
''' + body + '''
	return 0;
out_release:
	release_firmware(mdt);
	return ret;
}

'''
wrapper = '''static int qseecom_tee_supp_load_app(struct tee_context *ctx,
				     struct tee_ioctl_open_session_arg *arg,
				     struct tee_param *param)
{
	struct qseecom_tee_context *ctxdata = ctx->data;
	struct qseecom_tee *qtee = ctxdata->qtee;
	char app_name[QSEECOM_TEE_MAX_APP_NAME];
	u32 app_id, app_gen = 0;
	int ret;

	if (arg->num_params != 1)
		return -EINVAL;
	ret = qseecom_tee_get_app_name(&param[0], app_name, sizeof(app_name));
	if (ret)
		return ret;
	/* A shared service image must never be treated as an ordinary app. */
	if (!strcmp(app_name, "cmnlib") || !strcmp(app_name, "cmnlib64"))
		return -EINVAL;

	guard(mutex)(&qtee->load_lock);
	app_id = qseecom_tee_app_get(qtee, app_name, &app_gen);
	if (app_id)
		goto add_session;
	ret = qcom_scm_qseecom_app_get_id(app_name, &app_id);
	if (!ret)
		goto add_session;
	if (ret != -ENOENT)
		return ret;

	/* Stock aura loads cmnlib before a 32-bit application. Successful
	 * service loading is cached by SCM for this boot, not this module.
	 */
	ret = qseecom_tee_load_image(qtee, "cmnlib", true, NULL);
	if (ret)
		return ret;
	ret = qseecom_tee_load_image(qtee, app_name, false, &app_id);
	if (ret)
		return ret;
	ret = qseecom_tee_app_remember(qtee, app_name, app_id, &app_gen);
	if (ret) {
		if (qcom_scm_qseecom_app_shutdown(app_id))
			dev_err(qtee->dev, "app %u stranded after load failure\\n", app_id);
		return ret;
	}

add_session:
	ret = qseecom_tee_session_add(ctxdata, app_id, app_gen, NULL, &arg->session);
	if (ret) {
		qseecom_tee_app_put(qtee, app_id, app_gen);
		return ret;
	}
	arg->ret = 0;
	arg->ret_origin = 0;
	return 0;
}
'''
s = s[:start] + helper + wrapper + s[end:]
path.write_text(s)
print('Added explicit-load cmnlib startup and session lifetime fixes.')
