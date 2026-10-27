package main

import rego.v1

deny contains msg if {
	some type in tagged_types
	some name, items in input.resource[type]
	tags := tag_map(items[0])
	missing_text(object.get(tags, "data_classification", ""))
	msg := sprintf("nordpay.tags.data_classification: %s.%s is missing data_classification", [type, name])
}

deny contains msg if {
	some type in tagged_types
	some name, items in input.resource[type]
	tags := tag_map(items[0])
	missing_text(object.get(tags, "owner", ""))
	msg := sprintf("nordpay.tags.owner: %s.%s is missing owner", [type, name])
}

missing_text(value) if {
	value == ""
}

missing_text(value) if {
	not is_string(value)
}
