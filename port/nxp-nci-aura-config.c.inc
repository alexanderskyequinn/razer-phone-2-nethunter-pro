/* Original RC2 board initialization, after CORE_INIT and before discovery. */
static int nxp_nci_aura_prop_rsp(struct nci_dev *ndev, struct sk_buff *skb)
{
	nci_req_complete(ndev, skb->len ? skb->data[0] : NCI_STATUS_FAILED);
	return 0;
}

static const struct nci_driver_ops nxp_nci_aura_prop_ops[] = {
	{ .opcode = nci_opcode_pack(NCI_GID_PROPRIETARY, 0x02),
	  .rsp = nxp_nci_aura_prop_rsp },
	{ .opcode = nci_opcode_pack(NCI_GID_PROPRIETARY, 0x15),
	  .rsp = nxp_nci_aura_prop_rsp },
};

static int nxp_nci_aura_post_setup(struct nci_dev *ndev)
{
	struct nxp_nci_info *info = nci_get_drvdata(ndev);
	const struct firmware *config;
	const u8 *p;
	size_t offset;
	int ret;

	if (!of_machine_is_compatible("razer,aura"))
		return 0;

	ret = request_firmware(&config, "nxp/razer-aura-nci-config.bin", info->pdev);
	if (ret)
		return ret;

	/* Validate the complete stream before sending any configuration. */
	ret = -EINVAL;
	if (!config->size || config->size > 8192)
		goto out;
	for (offset = 0; offset < config->size; offset += 3 + p[2]) {
		if (config->size - offset < 3)
			goto out;
		p = config->data + offset;
		if (p[2] > config->size - offset - 3)
			goto out;
		if (!((p[0] == 0x20 && p[1] == 0x02 && p[2] >= 1) ||
		      (p[0] == 0x2f && p[1] == 0x02 && p[2] == 0) ||
		      (p[0] == 0x2f && p[1] == 0x15 && p[2] == 1 && p[3] == 0)))
			goto out;
	}
	for (offset = 0; offset < config->size; offset += 3 + p[2]) {
		p = config->data + offset;
		if (p[0] == 0x2f)
			ret = nci_prop_cmd(ndev, p[1], p[2], p + 3);
		else
			ret = nci_core_cmd(ndev, NCI_OP_CORE_SET_CONFIG_CMD, p[2], p + 3);
		if (ret) {
			dev_err(info->pdev, "Razer NFC configuration at %zu failed: %d\n", offset, ret);
			goto out;
		}
	}
	dev_info(info->pdev, "Razer NFC board configuration applied\n");
out:
	release_firmware(config);
	return ret;
}
