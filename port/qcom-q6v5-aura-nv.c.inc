/* Match RC2's pil_mss_reset_load_mba() FIH NV assignment before MBA starts. */
static int q6v5_aura_assign_nv(struct q6v5 *qproc)
{
	static bool assigned;
	struct qcom_scm_vmperm perms[] = {
		{ .vmid = QCOM_SCM_VMID_HLOS, .perm = QCOM_SCM_PERM_RW },
		{ .vmid = QCOM_SCM_VMID_MSS_MSA, .perm = QCOM_SCM_PERM_RW },
	};
	struct device_node *node;
	struct reserved_mem *region;
	u64 owners = BIT(QCOM_SCM_VMID_HLOS);
	int ret;

	if (!of_machine_is_compatible("razer,aura") || assigned)
		return 0;

	node = of_find_node_by_path("/reserved-memory/fih-nv@af000000");
	if (!node)
		return -ENODEV;
	region = of_reserved_mem_lookup(node);
	if (!of_property_read_bool(node, "no-map") || !region ||
	    region->base != 0xaf000000 || region->size != SZ_8M) {
		of_node_put(node);
		return -EINVAL;
	}
	of_node_put(node);

	ret = qcom_scm_assign_mem(region->base, region->size, &owners,
				  perms, ARRAY_SIZE(perms));
	if (ret) {
		dev_err(qproc->dev, "Razer modem NV memory assignment failed: %d\n", ret);
		return ret;
	}

	/* Stock leaves this reserved region shared for the rest of the boot. */
	assigned = true;
	dev_info(qproc->dev, "Razer modem NV memory shared at %pa, size %pa\n",
		 &region->base, &region->size);
	return 0;
}
