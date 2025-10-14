terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.110"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = "<YOUR_SUBSCRIPTION_ID>" # 🔹 Replace with target subscription
}

locals {
  # Region and logical mappings from your sheet
  crg_config = {
    CIN = [
      { zone = 1, logical_zone = 3 },
      { zone = 2, logical_zone = 2 },
      { zone = 3, logical_zone = 1 }
    ]
    SEA = [
      { zone = 1, logical_zone = 3 },
      { zone = 2, logical_zone = 2 },
      { zone = 3, logical_zone = 1 }
    ]
    EUS = [
      { zone = 1, logical_zone = 3 },
      { zone = 2, logical_zone = 2 },
      { zone = 3, logical_zone = 1 }
    ]
    WUS = [
      { zone = 1, logical_zone = 3 },
      { zone = 2, logical_zone = 2 },
      { zone = 3, logical_zone = 1 }
    ]
  }

  # Standard VM SKU
  vm_sku = "Standard_D8ds_v5"
}

# Create CRGs dynamically
resource "azurerm_capacity_reservation_group" "crg" {
  for_each = { for region, zones in local.crg_config : region => zones }

  name                = "${each.key}-crg-zone-${each.value[0].zone}"
  location            = lower(each.key)
  resource_group_name = "rg-${lower(each.key)}-capacity"

  # Optional tags for clarity
  tags = {
    environment = "prod"
    region      = each.key
    zone        = tostring(each.value[0].zone)
    logicalZone = tostring(each.value[0].logical_zone)
  }
}

# Example of a Capacity Reservation inside each CRG
resource "azurerm_capacity_reservation" "vm_reservation" {
  for_each = toset(flatten([
    for region, zones in local.crg_config : [
      for zone in zones : "${region}-${zone.zone}"
    ]
  ]))

  name                        = "cr-${each.key}"
  capacity_reservation_group_id = azurerm_capacity_reservation_group.crg[split("-", each.key)[0]].id
  sku {
    name = local.vm_sku
    capacity = 125 # 🔹 You can adjust per sheet (number of VMs reserved)
  }
  location            = lower(split("-", each.key)[0])
  zone                = tonumber(split("-", each.key)[1])
  resource_group_name = "rg-${lower(split("-", each.key)[0])}-capacity"
}
