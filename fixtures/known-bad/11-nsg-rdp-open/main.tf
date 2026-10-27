resource "azurerm_network_security_group" "edge" {
  name                = "nsg-rdp"
  location            = "germanywestcentral"
  resource_group_name = "rg-nordpay-prod"
  tags = {
    data_classification = "internal"
    owner               = "payments-platform"
  }
  security_rule {
    name                   = "rdp"
    priority               = 100
    direction              = "Inbound"
    access                 = "Allow"
    protocol               = "Tcp"
    source_port_range      = "*"
    destination_port_range = "3389"
    # Same Checkov internet-address list as the SSH fixture: "*" is matched, "0.0.0.0/0" is not.
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}
