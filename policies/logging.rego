package main

import rego.v1

deny contains msg if {
	some name, items in input.resource.azurerm_log_analytics_workspace
	body := items[0]
	days := object.get(body, "retention_in_days", 0)
	days < 90
	msg := sprintf("nordpay.logging.retention: azurerm_log_analytics_workspace.%s keeps logs for %v days; NordPay wants at least 90", [name, days])
}
