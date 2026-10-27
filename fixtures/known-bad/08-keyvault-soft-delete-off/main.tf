resource "azurerm_key_vault" "payments" {
  name                          = "kv-fixture-nordpay"
  location                      = "germanywestcentral"
  resource_group_name           = "rg-nordpay-prod"
  tenant_id                     = "00000000-0000-0000-0000-000000000001"
  sku_name                      = "standard"
  purge_protection_enabled      = true
  soft_delete_enabled           = false
  public_network_access_enabled = false
  enable_rbac_authorization     = true
  tags = {
    data_classification = "internal"
    owner               = "payments-platform"
  }
}
