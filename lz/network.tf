resource "azurerm_virtual_network" "pay" {
  name                = "vnet-nordpay-prod"
  location            = local.location
  resource_group_name = azurerm_resource_group.pay.name
  address_space       = ["10.4.0.0/16"]
  tags                = local.tags_internal
}

resource "azurerm_network_security_group" "app" {
  name                = "nsg-nordpay-app"
  location            = local.location
  resource_group_name = azurerm_resource_group.pay.name
  tags                = local.tags_internal

  security_rule {
    name                       = "https-from-app-subnet"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "10.4.1.0/24"
    destination_address_prefix = "10.4.1.0/24"
  }
}

resource "azurerm_subnet" "app" {
  name                 = "snet-app"
  resource_group_name  = azurerm_resource_group.pay.name
  virtual_network_name = azurerm_virtual_network.pay.name
  address_prefixes     = ["10.4.1.0/24"]
}

resource "azurerm_subnet_network_security_group_association" "app" {
  subnet_id                 = azurerm_subnet.app.id
  network_security_group_id = azurerm_network_security_group.app.id
}
