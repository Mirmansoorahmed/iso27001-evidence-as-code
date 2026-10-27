package main

import rego.v1

# NordPay offline helpers. Conftest's HCL2 parser leaves locals as objects
# and leaves references as ${...} strings. These helpers resolve a local
# reference one level deep. They do not evaluate variables or functions.

tagged_types := {
	"azurerm_resource_group",
	"azurerm_virtual_network",
	"azurerm_network_security_group",
	"azurerm_storage_account",
	"azurerm_key_vault",
	"azurerm_log_analytics_workspace",
	"azurerm_linux_web_app",
	"azurerm_app_service",
	"azurerm_service_plan",
	"azurerm_app_service_plan",
	"azurerm_recovery_services_vault",
}

location_types := tagged_types

diag_types := {
	"azurerm_storage_account",
	"azurerm_key_vault",
	"azurerm_linux_web_app",
	"azurerm_app_service",
}

# Regions NordPay accepts for payment data. This is a company allow-list,
# not a claim about where a regulator says data must live.
eu_locations := {
	"germanywestcentral",
	"germanynorth",
	"westeurope",
	"northeurope",
	"swedencentral",
	"francecentral",
	"francesouth",
	"polandcentral",
	"norwayeast",
	"norwaywest",
	"switzerlandnorth",
	"switzerlandwest",
	"italynorth",
	"spaincentral",
	"belgiumcentral",
	"austriaeast",
}

local_object(name) := val if {
	some block in input.locals
	is_object(block[name])
	val := block[name]
}

local_string(name) := val if {
	some block in input.locals
	is_string(block[name])
	val := block[name]
}

tag_map(body) := tags if {
	raw := body.tags
	is_object(raw)
	tags := raw
} else := tags if {
	raw := body.tags
	is_string(raw)
	match := regex.find_all_string_submatch_n(`^\$\{local\.([A-Za-z0-9_]+)\}$`, raw, 1)
	count(match) == 1
	tags := local_object(match[0][1])
} else := {}

location_of(body) := loc if {
	raw := body.location
	is_string(raw)
	not startswith(raw, "${")
	loc := raw
} else := loc if {
	raw := body.location
	is_string(raw)
	match := regex.find_all_string_submatch_n(`^\$\{local\.([A-Za-z0-9_]+)\}$`, raw, 1)
	count(match) == 1
	loc := local_string(match[0][1])
}

in_eu(body) if {
	loc := location_of(body)
	loc in eu_locations
}
