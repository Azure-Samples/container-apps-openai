
variable "name" {
  description = "(Required) Specifies the name of the managed environment."
  type        = string
}

variable "resource_group_name" {
  description = "(Required) Specifies the resource group name"
  type = string
}

variable "tags" {
  description = "(Optional) Specifies the tags of the log analytics workspace"
  type        = map(any)
  default     = {}
}

variable "location" {
  description = "(Required) Specifies the supported Azure location where the resource exists. Changing this forces a new resource to be created."
  type        = string
}

variable "infrastructure_subnet_id" {
  description = "(Optional) Specifies resource id of the subnet hosting the Azure Container Apps environment."
  type        = string
}

variable "internal_load_balancer_enabled" {
  description = "(Optional) Should the Container Environment operate in Internal Load Balancing Mode? Defaults to false. Changing this forces a new resource to be created."
  type        = bool
  default     = false
}

variable "log_analytics_workspace_id" {
  description = "(Optional) The resource id of the Log Analytics Workspace used by the Container Apps Managed Environment."
  type        = string
}