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

variable "container_app_environment_name" {
  description = "(Required) Specifies the name of the Azure Container Apps Environment."
  type        = string
  default     = "Environment"
}

variable "container_registry_name" {
  description = "Specifies the name of the container registry"
  type        = string
  default     = "Registry"
}

variable "workload_managed_identity_name" {
  description = "(Required) Specifies the name of the workload user-defined managed identity"
  type = string
  default = "WorkloadIdentity"
}

variable "container_apps" {
  type = list(object({
    name          = string
    tags          = optional(map(string))
    revision_mode = string

    template = object({
      containers = set(object({
        name    = string
        image   = string
        args    = optional(list(string))
        command = optional(list(string))
        cpu     = string
        memory  = string
        env = optional(list(object({
          name        = string
          secret_name = optional(string)
          value       = optional(string)
        })))
        liveness_probe = optional(object({
          failure_count_threshold = optional(number)
          header = optional(object({
            name  = string
            value = string
          }))
          host             = optional(string)
          initial_delay    = optional(number, 1)
          interval_seconds = optional(number, 10)
          path             = optional(string)
          port             = number
          timeout          = optional(number, 1)
          transport        = string
        }))
        readiness_probe = optional(object({
          failure_count_threshold = optional(number)
          header = optional(object({
            name  = string
            value = string
          }))
          host                    = optional(string)
          interval_seconds        = optional(number, 10)
          path                    = optional(string)
          port                    = number
          success_count_threshold = optional(number, 3)
          timeout                 = optional(number)
          transport               = string
        }))
        startup_probe = optional(object({
          failure_count_threshold = optional(number)
          header = optional(object({
            name  = string
            value = string
          }))
          host             = optional(string)
          interval_seconds = optional(number, 10)
          path             = optional(string)
          port             = number
          timeout          = optional(number)
          transport        = string
        }))
        volume_mounts = optional(object({
          name = string
          path = string
        }))
      }))
      max_replicas    = optional(number)
      min_replicas    = optional(number)
      revision_suffix = optional(string)

      volume = optional(set(object({
        name         = string
        storage_name = optional(string)
        storage_type = optional(string)
      })))
    })

    ingress = optional(object({
      allow_insecure_connections = optional(bool, false)
      external_enabled           = optional(bool, false)
      target_port                = number
      transport                  = optional(string)
      traffic_weight = object({
        label           = optional(string)
        latest_revision = optional(string)
        revision_suffix = optional(string)
        percentage      = number
      })
    }))

    identity = optional(object({
      type         = string
      identity_ids = optional(list(string))
    }))

    dapr = optional(object({
      app_id       = string
      app_port     = number
      app_protocol = optional(string)
    }))

    registry = optional(list(object({
      server               = string
      username             = optional(string)
      password_secret_name = optional(string)
      identity             = optional(string)
    })))
  }))
  description = "The container apps to deploy."
  nullable    = false

  validation {
    condition     = length(var.container_apps) >= 1
    error_message = "At least one container should be provided."
  }
}

variable "container_app_secrets" {
  type = map(list(object({
    name  = string
    value = string
  })))
  default     = {}
  description = "(Optional) The secrets of the container apps. The key of the map should be aligned with the corresponding container app."
  nullable    = false
  sensitive   = true
}