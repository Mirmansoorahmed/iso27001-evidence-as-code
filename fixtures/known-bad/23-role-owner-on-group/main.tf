resource "azurerm_role_assignment" "group_owner" {
  scope                = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-nordpay-prod"
  role_definition_name = "Owner"
  principal_id         = "11111111-1111-1111-1111-111111111111"
}
