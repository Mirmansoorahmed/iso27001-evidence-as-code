package main

import rego.v1

deny contains msg if {
	some type in location_types
	some name, items in input.resource[type]
	body := items[0]
	not in_eu(body)
	msg := sprintf("nordpay.region.eu_only: %s.%s location is outside the EU allow-list or is not a literal/local", [type, name])
}
