variable "name_prefix" {
  description = "(Optional) A prefix for the name of all the resource groups and resources."
  type        = string
  nullable    = true
}

variable "location" {
  description = "(Required) Specifies the supported Azure location where the resource exists. Changing this forces a new resource to be created."
  type        = string
  default     = "WestEurope"
}

variable "resource_group_name" {
   description = "Name of the resource group in which the resources will be created"
   default     = "RG"
}

variable "tags" {
  description = "(Optional) Specifies tags for all the resources"
  default     = {
    createdWith = "Terraform",
    openAi = "true",
    containerApps = "true"
  }
}

variable "log_analytics_workspace_name" {
  description = "Specifies the name of the log analytics workspace"
  default     = "Workspace"
  type        = string
}

variable "log_analytics_retention_days" {
  description = "Specifies the number of days of the retention policy for the log analytics workspace."
  type        = number
  default     = 30
}

variable "vnet_name" {
  description = "Specifies the name of the virtual network"
  default     = "VNet"
  type        = string
}

variable "vnet_address_space" {
  description = "Specifies the address prefix of the virtual network"
  default     =  ["10.0.0.0/16"]
  type        = list(string)
}

variable "aca_subnet_name" {
  description = "Specifies the name of the subnet"
  default     = "ContainerApps"
  type        = string
}

variable "aca_subnet_address_prefix" {
  description = "Specifies the address prefix of the Azure Container Apps environment subnet"
  default     = ["10.0.0.0/20"]
  type        = list(string)
}

variable "private_endpoint_subnet_name" {
  description = "Specifies the name of the subnet"
  default     = "PrivateEndpoints"
  type        = string
}

variable "private_endpoint_subnet_address_prefix" {
  description = "Specifies the address prefix of the private endpoints subnet"
  default     = ["10.0.16.0/24"]
  type        = list(string)
}

variable "container_app_environment_name" {
  description = "(Required) Specifies the name of the Azure Container Apps Environment."
  type        = string
  default     = "Environment"
}

variable "internal_load_balancer_enabled" {
  description = "(Optional) specifies whether the Azure Container Apps Environment operate in Internal Load Balancing Mode? Defaults to false. Changing this forces a new resource to be created."
  type        = bool
  default     = false
}

variable "acr_name" {
  description = "Specifies the name of the container registry"
  type        = string
  default     = "Registry"
}

variable "acr_sku" {
  description = "Specifies the name of the container registry"
  type        = string
  default     = "Premium"

  validation {
    condition = contains(["Basic", "Standard", "Premium"], var.acr_sku)
    error_message = "The container registry sku is invalid."
  }
}

variable "acr_admin_enabled" {
  description = "Specifies whether admin is enabled for the container registry"
  type        = bool
  default     = true
}

variable "acr_georeplication_locations" {
  description = "(Optional) A list of Azure locations where the container registry should be geo-replicated."
  type        = list(string)
  default     = []
}

variable "openai_name" {
  description = "(Required) Specifies the name of the Azure OpenAI Service"
  type = string
  default = "OpenAI"
}

variable "openai_sku_name" {
  description = "(Optional) Specifies the sku name for the Azure OpenAI Service"
  type = string
  default = "S0"
}

variable "openai_custom_subdomain_name" {
  description = "(Optional) Specifies the custom subdomain name of the Azure OpenAI Service"
  type = string
  nullable = true
  default = ""
}

variable "openai_public_network_access_enabled" {
  description = "(Optional) Specifies whether public network access is allowed for the Azure OpenAI Service"
  type = bool
  default = true
}

variable "openai_deployments" {
  description = "(Optional) Specifies the deployments of the Azure OpenAI Service"
  type = list(object({
    name = string
    model = object({
      name = string
      version = string
    })
    rai_policy_name = string  
  }))
  default = [
    {
      name = "gpt-35-turbo-16k"
      model = {
        name = "gpt-35-turbo-16k"
        version = "0613"
      }
      rai_policy_name = ""
    },
    {
      name = "text-embedding-ada-002"
      model = {
        name = "text-embedding-ada-002"
        version = "2"
      }
      rai_policy_name = ""
    }
  ] 
}

variable "workload_managed_identity_name" {
  description = "(Required) Specifies the name of the workload user-defined managed identity"
  type = string
  default = "WorkloadIdentity"
}