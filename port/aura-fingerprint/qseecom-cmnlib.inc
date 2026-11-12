/* Razer downstream qseecomi.h: QSEE_OS / APP_MGR / command 0x07.
 * cmnlib remains resident for the boot lifetime, as in the stock driver.
 * Keep the success cache in SCM so a TEE frontend reload cannot reload it.
 */
static DEFINE_MUTEX(qcom_scm_qseecom_cmnlib_lock);
static bool qcom_scm_qseecom_cmnlib_loaded;

/**
 * qcom_scm_qseecom_load_cmnlib() - Load the shared 32-bit QSEE service image.
 * @img: Image assembled from cmnlib.mdt and its segments in TZ memory.
 * @mdt_len: Metadata size in bytes.
 * @img_len: Total assembled size in bytes.
 *
 * Only called for an explicit privileged application load, never at probe.
 * Success is remembered until reboot. No service-image unload is exposed:
 * other trusted applications may depend on the shared library.
 *
 * Return: Zero on success, negative errno on failure.
 */
int qcom_scm_qseecom_load_cmnlib(void *img, size_t mdt_len, size_t img_len)
{
	struct qcom_scm_qseecom_resp res = {};
	struct qcom_scm_desc desc = {};
	phys_addr_t phys;
	int ret;

	if (!img || !mdt_len || mdt_len > img_len)
		return -EINVAL;
	phys = qcom_tzmem_to_phys(img);
	if (!phys)
		return -EINVAL;

	guard(mutex)(&qcom_scm_qseecom_cmnlib_lock);
	if (qcom_scm_qseecom_cmnlib_loaded)
		return 0;

	desc.owner = QSEECOM_TZ_OWNER_QSEE_OS;
	desc.svc = QSEECOM_TZ_SVC_APP_MGR;
	desc.cmd = 0x07;
	desc.arginfo = QCOM_SCM_ARGS(3);
	desc.args[0] = mdt_len;
	desc.args[1] = img_len;
	desc.args[2] = phys;
	ret = qcom_scm_qseecom_call(&desc, &res);
	if (ret)
		return ret;
	if (res.result != QSEECOM_RESULT_SUCCESS) {
		dev_err(__scm->dev, "qseecom: cmnlib load rejected (%llu)\n",
			res.result);
		return -EIO;
	}
	qcom_scm_qseecom_cmnlib_loaded = true;
	return 0;
}
EXPORT_SYMBOL_GPL(qcom_scm_qseecom_load_cmnlib);
