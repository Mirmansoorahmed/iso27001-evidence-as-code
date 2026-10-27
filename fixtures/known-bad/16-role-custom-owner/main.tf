resource "azurerm_role_definition" "ownerish" {
  name  = "nordpay-custom-owner"
  scope = "/subscriptions/00000000-0000-0000-0000-000000000000"
  permissions {
    actions = ["*"]
  }
  assignable_scopes = ["/subscriptions/00000000-0000-0000-0000-000000000000"]
}
