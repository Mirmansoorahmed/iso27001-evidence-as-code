package main

import rego.v1

deny contains msg if {
	prod_present
	not vault_present
	msg := "nordpay.backup.vault_for_prod: a prod-tagged data resource is present and this module has no recovery services vault"
}

prod_present if {
	some type in diag_types
	some name, items in input.resource[type]
	object.get(tag_map(items[0]), "environment", "") == "prod"
}

vault_present if {
	input.resource.azurerm_recovery_services_vault
}
