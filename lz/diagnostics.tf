resource "azurerm_monitor_diagnostic_setting" "storage" {
  name                       = "diag-storage"
  target_resource_id         = azurerm_storage_account.payments.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.sec.id

  metric {
    category = "Transaction"
    enabled  = true
  }
}

resource "azurerm_monitor_diagnostic_setting" "keyvault" {
  name                       = "diag-keyvault"
  target_resource_id         = azurerm_key_vault.payments.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.sec.id

  enabled_log {
    category = "AuditEvent"
  }
}

resource "azurerm_monitor_diagnostic_setting" "api" {
  name                       = "diag-api"
  target_resource_id         = azurerm_linux_web_app.api.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.sec.id

  enabled_log {
    category = "AppServiceHTTPLogs"
  }
}
