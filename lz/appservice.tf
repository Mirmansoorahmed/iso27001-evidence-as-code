resource "azurerm_service_plan" "api" {
  name                = "asp-nordpay-prod"
  resource_group_name = azurerm_resource_group.pay.name
  location            = local.location
  os_type             = "Linux"
  sku_name            = "P1v3"
  tags                = local.tags_internal
}

resource "azurerm_linux_web_app" "api" {
  name                = "app-nordpay-api"
  resource_group_name = azurerm_resource_group.pay.name
  location            = local.location
  service_plan_id     = azurerm_service_plan.api.id
  https_only          = true
  tags                = local.tags_confidential

  site_config {
    minimum_tls_version      = "1.2"
    ftps_state               = "Disabled"
    remote_debugging_enabled = false
    always_on                = true
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
