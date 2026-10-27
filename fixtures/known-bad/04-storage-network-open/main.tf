resource "azurerm_storage_account" "payments" {

  name                            = "stnetopen"
  resource_group_name             = "rg-nordpay-prod"
  location                        = "germanywestcentral"
  account_tier                    = "Standard"
  account_replication_type        = "GZRS"
  account_kind                    = "StorageV2"
  enable_https_traffic_only       = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  public_network_access_enabled   = true

  tags = {
    data_classification = "confidential"
    owner               = "payments-platform"
  }
  network_rules {
    default_action = "Allow"
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
