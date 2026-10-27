package main

import rego.v1

deny contains msg if {
	some name, items in input.resource.azurerm_key_vault
	body := items[0]
	tags := tag_map(body)
	object.get(tags, "data_classification", "") == "confidential"
	object.get(body, "purge_protection_enabled", false) != true
	msg := sprintf("nordpay.keyvault.purge_protection_confidential: azurerm_key_vault.%s is confidential and purge protection is not on", [name])
}
