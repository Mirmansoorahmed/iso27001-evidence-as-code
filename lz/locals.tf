# Tags and the region are locals, not variables. The Rego policies resolve
# local.* references and do not evaluate var.* . That is a limitation of the
# offline parser, so the landing zone stays inside what the policies can see.

locals {
  location = "germanywestcentral"

  tags_confidential = {
    data_classification = "confidential"
    owner               = "payments-platform"
    environment         = "prod"
    managed_by          = "terraform"
  }

  tags_internal = {
    data_classification = "internal"
    owner               = "payments-platform"
    environment         = "prod"
    managed_by          = "terraform"
  }
}

resource "azurerm_resource_group" "pay" {
  name     = "rg-nordpay-prod"
  location = local.location
  tags     = local.tags_internal
}
