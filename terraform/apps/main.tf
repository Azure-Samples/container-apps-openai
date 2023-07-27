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

module "container_apps" {
  source                         = "./modules/container_app"
  resource_group_name            = var.resource_group_name
  container_app_environment_name = var.container_app_environment_name
  container_registry_name        = var.container_registry_name
  workload_managed_identity_name = var.workload_managed_identity_name
  container_apps                 = var.container_apps
  container_app_secrets          = var.container_app_secrets
  tags                           = var.tags
}