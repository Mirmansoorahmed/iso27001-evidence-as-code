resource "azurerm_recovery_services_vault" "pay" {
  name                = "rsv-nordpay-prod"
  location            = local.location
  resource_group_name = azurerm_resource_group.pay.name
  sku                 = "Standard"
  tags                = local.tags_confidential
}
