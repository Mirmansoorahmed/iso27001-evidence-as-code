resource "azurerm_monitor_log_profile" "activity" {
  name       = "nordpay-activity-short"
  categories = ["Action", "Delete", "Write"]
  locations  = ["germanywestcentral"]
  retention_policy {
    enabled = true
    days    = 30
  }
  storage_account_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-nordpay-prod/providers/Microsoft.Storage/storageAccounts/stnordpayprod001"
}
