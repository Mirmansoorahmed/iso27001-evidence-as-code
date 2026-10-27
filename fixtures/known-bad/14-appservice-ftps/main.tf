resource "azurerm_linux_web_app" "api" {
  name                = "app-nordpay-fixture"
  location            = "germanywestcentral"
  resource_group_name = "rg-nordpay-prod"
  service_plan_id     = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-nordpay-prod/providers/Microsoft.Web/serverFarms/asp-nordpay-prod"
  https_only          = true
  tags = {
    data_classification = "confidential"
    owner               = "payments-platform"
  }
  site_config {
    minimum_tls_version      = "1.2"
    ftps_state               = "AllAllowed"
    remote_debugging_enabled = false
  }
  auth_settings {
    enabled = true
  }
  logs {
    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 35
      }
    }
  }
}
