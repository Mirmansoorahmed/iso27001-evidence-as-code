resource "azurerm_key_vault" "payments" {
  name                          = "kv-nordpay-prod"
  location                      = local.location
  resource_group_name           = azurerm_resource_group.pay.name
  tenant_id                     = "00000000-0000-0000-0000-000000000001"
  sku_name                      = "standard"
  purge_protection_enabled      = true
  public_network_access_enabled = false
  enable_rbac_authorization     = true
  tags                          = local.tags_confidential
}
