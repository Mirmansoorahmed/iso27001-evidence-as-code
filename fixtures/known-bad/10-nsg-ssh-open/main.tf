resource "azurerm_network_security_group" "edge" {
  name                = "nsg-ssh"
  location            = "germanywestcentral"
  resource_group_name = "rg-nordpay-prod"
  tags = {
    data_classification = "internal"
    owner               = "payments-platform"
  }
  security_rule {
    name                   = "ssh"
    priority               = 100
    direction              = "Inbound"
    access                 = "Allow"
    protocol               = "Tcp"
    source_port_range      = "*"
    destination_port_range = "22"
    # Checkov 3.2.449 matches internet sources by exact string. "*" is in that
    # list; the CIDR "0.0.0.0/0" is not, so this fixture uses the form the check sees.
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}
