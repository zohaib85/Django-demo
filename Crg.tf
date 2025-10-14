variable "subscription_id" {
  description = "Azure Subscription ID for Capacity Reservations"
  type        = string
}

variable "vm_sku" {
  description = "VM SKU for capacity reservation"
  type        = string
  default     = "Standard_D8ds_v5"
}

variable "crg_config" {
  description = "Configuration for regions, zones, and required capacity"
  type = map(list(object({
    zone          = number
    logical_zone  = number
    capacity      = number
  })))
}


subscription_id = "<YOUR_SUBSCRIPTION_ID>" # 🔹 Replace per subscription

crg_config = {
  CIN = [
    { zone = 1, logical_zone = 3, capacity = 135 },
    { zone = 2, logical_zone = 2, capacity = 125 },
    { zone = 3, logical_zone = 1, capacity = 125 }
  ]
  SEA = [
    { zone = 1, logical_zone = 3, capacity = 135 },
    { zone = 2, logical_zone = 2, capacity = 125 },
    { zone = 3, logical_zone = 1, capacity = 125 }
  ]
  EUS = [
    { zone = 1, logical_zone = 3, capacity = 132 },
    { zone = 2, logical_zone = 2, capacity = 142 },
    { zone = 3, logical_zone = 1, capacity = 132 }
  ]
  WUS = [
    { zone = 1, logical_zone = 3, capacity = 142 },
    { zone = 2, logical_zone = 2, capacity = 132 },
    { zone = 3, logical_zone = 1, capacity = 50 }
  ]
}

vm_sku = "Standard_D8ds_v5"


# =======================
# Resource Groups
# =======================
resource "azurerm_resource_group" "crg_rg" {
  for_each = var.crg_config

  name     = "rg-${lower(each.key)}-capacity"
  location = lower(each.key)

  tags = {
    region = each.key
    type   = "capacity"
  }
}

# =======================
# Capacity Reservation Groups
# =======================
resource "azurerm_capacity_reservation_group" "crg" {
  for_each = var.crg_config

  name                = "${each.key}-crg"
  location            = lower(each.key)
  resource_group_name = azurerm_resource_group.crg_rg[each.key].name

  tags = {
    region  = each.key
    purpose = "vdi-capacity"
  }
}

# =======================
# Capacity Reservations
# =======================
resource "azurerm_capacity_reservation" "vm_reservation" {
  for_each = {
    for region, zones in var.crg_config : 
    for zone in zones : "${region}-${zone.zone}" => {
      region        = region
      zone          = zone.zone
      capacity      = zone.capacity
      logical_zone  = zone.logical_zone
    }
  }

  name                          = "cr-${each.key}"
  location                      = lower(each.value.region)
  resource_group_name           = azurerm_resource_group.crg_rg[each.value.region].name
  zone                          = each.value.zone
  capacity_reservation_group_id = azurerm_capacity_reservation_group.crg[each.value.region].id

  sku {
    name     = var.vm_sku
    capacity = each.value.capacity
  }

  tags = {
    region       = each.value.region
    zone         = tostring(each.value.zone)
    logical_zone = tostring(each.value.logical_zone)
  }
}
