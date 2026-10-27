resource "azurerm_storage_account" "payments" {
  name                            = "stnordpayprod001"
  resource_group_name             = azurerm_resource_group.pay.name
  location                        = local.location
  account_tier                    = "Standard"
  account_replication_type        = "GZRS"
  account_kind                    = "StorageV2"
  enable_https_traffic_only       = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  public_network_access_enabled   = false
  tags                            = local.tags_confidential

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
