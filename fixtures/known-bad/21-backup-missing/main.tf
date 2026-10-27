resource "azurerm_storage_account" "payments" {

  name                            = "stnovault"
  resource_group_name             = "rg-nordpay-prod"
  location                        = "germanywestcentral"
  account_tier                    = "Standard"
  account_replication_type        = "GZRS"
  account_kind                    = "StorageV2"
  enable_https_traffic_only       = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  public_network_access_enabled   = false

  tags = {
    data_classification = "confidential"
    owner               = "payments-platform"
    environment         = "prod"
  }
  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices"]
  }
  queue_properties {
    logging {
      delete                = true
      read                  = true
      write                 = true
      version               = "1.0"
      retention_policy_days = 10
    }
  }
}

resource "azurerm_monitor_diagnostic_setting" "payments" {
  name                       = "diag-payments"
  target_resource_id         = azurerm_storage_account.payments.id
  log_analytics_workspace_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-nordpay-prod/providers/Microsoft.OperationalInsights/workspaces/log-nordpay-prod"
  metric {
    category = "Transaction"
    enabled  = true
  }
}
