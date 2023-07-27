terraform {
  required_version = ">= 1.3"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.65"
    }
  }
}

provider "azurerm" {
  features {}
}

data "azurerm_client_config" "current" {
}

resource "random_string" "prefix" {
  length  = 6
  special = false
  upper   = false
  numeric = false
}

resource "azurerm_resource_group" "rg" {
  name     = var.name_prefix == null ? "${random_string.prefix.result}${var.resource_group_name}" : "${var.name_prefix}${var.resource_group_name}"
  location = var.location
  tags     = var.tags
}

module "log_analytics_workspace" {
  source                           = "./modules/log_analytics"
  name                             = var.name_prefix == null ? "${random_string.prefix.result}${var.log_analytics_workspace_name}" : "${var.name_prefix}${var.log_analytics_workspace_name}"
  location                         = var.location
  resource_group_name              = azurerm_resource_group.rg.name
  tags                             = var.tags
}

module "virtual_network" {
  source                           = "./modules/virtual_network"
  resource_group_name              = azurerm_resource_group.rg.name
  vnet_name                        = var.name_prefix == null ? "${random_string.prefix.result}${var.vnet_name}" : "${var.name_prefix}${var.vnet_name}"
  location                         = var.location
  address_space                    = var.vnet_address_space
  tags                             = var.tags
  log_analytics_workspace_id       = module.log_analytics_workspace.id
  log_analytics_retention_days     = var.log_analytics_retention_days

  subnets = [
    {
      name : var.aca_subnet_name
      address_prefixes : var.aca_subnet_address_prefix
      private_endpoint_network_policies_enabled : true
      private_link_service_network_policies_enabled : false
    },
    {
      name : var.private_endpoint_subnet_name
      address_prefixes : var.private_endpoint_subnet_address_prefix
      private_endpoint_network_policies_enabled : true
      private_link_service_network_policies_enabled : false
    }
  ]
}

module "acr_private_dns_zone" {
  source                       = "./modules/private_dns_zone"
  name                         = "privatelink.azurecr.io"
  resource_group_name          = azurerm_resource_group.rg.name
  tags                         = var.tags
  virtual_networks_to_link     = {
    (module.virtual_network.name) = {
      subscription_id = data.azurerm_client_config.current.subscription_id
      resource_group_name = azurerm_resource_group.rg.name
    }
  }
}

module "openai_private_dns_zone" {
  source                       = "./modules/private_dns_zone"
  name                         = "privatelink.openai.azure.com"
  resource_group_name          = azurerm_resource_group.rg.name
  tags                         = var.tags
  virtual_networks_to_link     = {
    (module.virtual_network.name) = {
      subscription_id = data.azurerm_client_config.current.subscription_id
      resource_group_name = azurerm_resource_group.rg.name
    }
  }
}

module "openai_private_endpoint" {
  source                         = "./modules/private_endpoint"
  name                           = "${module.openai.name}PrivateEndpoint"
  location                       = var.location
  resource_group_name            = azurerm_resource_group.rg.name
  subnet_id                      = module.virtual_network.subnet_ids[var.private_endpoint_subnet_name]
  tags                           = var.tags
  private_connection_resource_id = module.openai.id
  is_manual_connection           = false
  subresource_name               = "account"
  private_dns_zone_group_name    = "OpenAiPrivateDnsZoneGroup"
  private_dns_zone_group_ids     = [module.openai_private_dns_zone.id]
}

module "acr_private_endpoint" {
  source                         = "./modules/private_endpoint"
  name                           = "${module.container_registry.name}PrivateEndpoint"
  location                       = var.location
  resource_group_name            = azurerm_resource_group.rg.name
  subnet_id                      = module.virtual_network.subnet_ids[var.private_endpoint_subnet_name]
  tags                           = var.tags
  private_connection_resource_id = module.container_registry.id
  is_manual_connection           = false
  subresource_name               = "registry"
  private_dns_zone_group_name    = "AcrPrivateDnsZoneGroup"
  private_dns_zone_group_ids     = [module.acr_private_dns_zone.id]
}

module "openai" {
  source                        = "./modules/openai"
  name                          = var.name_prefix == null ? "${random_string.prefix.result}${var.openai_name}" : "${var.name_prefix}${var.openai_name}"
  location                      = var.location
  resource_group_name           = azurerm_resource_group.rg.name
  sku_name                      = var.openai_sku_name
  tags                          = var.tags
  deployments                   = var.openai_deployments
  custom_subdomain_name         = var.openai_custom_subdomain_name == "" || var.openai_custom_subdomain_name == null ? var.name_prefix == null ? lower("${random_string.prefix.result}${var.openai_name}") : lower("${var.name_prefix}${var.openai_name}") : lower(var.openai_custom_subdomain_name)
  public_network_access_enabled = var.openai_public_network_access_enabled
  log_analytics_workspace_id    = module.log_analytics_workspace.id
  log_analytics_retention_days  = var.log_analytics_retention_days
}

module "container_registry" {
  source                       = "./modules/container_registry"
  name                         = var.name_prefix == null ? "${random_string.prefix.result}${var.acr_name}" : "${var.name_prefix}${var.acr_name}"
  resource_group_name          = azurerm_resource_group.rg.name
  location                     = var.location
  sku                          = var.acr_sku
  admin_enabled                = var.acr_admin_enabled
  georeplication_locations     = var.acr_georeplication_locations
  log_analytics_workspace_id   = module.log_analytics_workspace.id
  log_analytics_retention_days = var.log_analytics_retention_days
  tags                         = var.tags

}

module "workload_managed_identity" {
  source                       = "./modules/managed_identity"
  name                         = var.name_prefix == null ? "${random_string.prefix.result}${var.workload_managed_identity_name}" : "${var.name_prefix}${var.workload_managed_identity_name}"
  resource_group_name          = azurerm_resource_group.rg.name
  location                     = var.location
  openai_id                    = module.openai.id
  acr_id                       = module.container_registry.id
  tags                         = var.tags
}

module "container_app_environment" {
  source                           = "./modules/container_app_environment"
  name                             = var.name_prefix == null ? "${random_string.prefix.result}${var.container_app_environment_name}" : "${var.name_prefix}${var.container_app_environment_name}"
  location                         = var.location
  resource_group_name              = azurerm_resource_group.rg.name
  tags                             = var.tags
  infrastructure_subnet_id         = module.virtual_network.subnet_ids[var.aca_subnet_name] 
  internal_load_balancer_enabled   = var.internal_load_balancer_enabled
  log_analytics_workspace_id       = module.log_analytics_workspace.id
}