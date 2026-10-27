resource "azurerm_role_assignment" "ops_reader" {
  scope                = azurerm_resource_group.pay.id
  role_definition_name = "Reader"
  principal_id         = "11111111-1111-1111-1111-111111111111"
}
