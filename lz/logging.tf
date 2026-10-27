resource "azurerm_log_analytics_workspace" "sec" {
  name                = "log-nordpay-prod"
  location            = local.location
  resource_group_name = azurerm_resource_group.pay.name
  sku                 = "PerGB2018"
  retention_in_days   = 90
  tags                = local.tags_confidential
}

resource "azurerm_monitor_log_profile" "activity" {
  name = "nordpay-activity"

  categories = [
    "Action",
    "Delete",
    "Write",
  ]

  locations = [
    "germanywestcentral",
    "global",
  ]

  retention_policy {
    enabled = true
    days    = 365
  }

  storage_account_id = azurerm_storage_account.payments.id
}
