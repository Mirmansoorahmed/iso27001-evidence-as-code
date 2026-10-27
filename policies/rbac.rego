package main

import rego.v1

# Standing Owner on the subscription. Owner on a resource group is out of
# scope for this rule; that boundary is deliberate and tested.
deny contains msg if {
	some name, items in input.resource.azurerm_role_assignment
	body := items[0]
	object.get(body, "role_definition_name", "") == "Owner"
	scope := object.get(body, "scope", "")
	is_string(scope)
	startswith(scope, "/subscriptions/")
	not contains(scope, "/resourceGroups/")
	not contains(scope, "/providers/")
	msg := sprintf("nordpay.rbac.no_subscription_owner: azurerm_role_assignment.%s grants Owner on a subscription", [name])
}
