package main

import rego.v1

deny contains msg if {
	some type in diag_types
	some name, items in input.resource[type]
	tags := tag_map(items[0])
	object.get(tags, "environment", "") == "prod"
	not diag_covers(type, name)
	msg := sprintf("nordpay.diagnostics.required: %s.%s is tagged prod and this module has no diagnostic setting for it", [type, name])
}

diag_covers(type, name) if {
	needle := sprintf("%s.%s", [type, name])
	some dname, items in input.resource.azurerm_monitor_diagnostic_setting
	target := items[0].target_resource_id
	is_string(target)
	contains(target, needle)
}
