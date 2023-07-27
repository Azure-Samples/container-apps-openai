data "azurerm_container_app_environment" "container_app_environment" {
  name                 = var.container_app_environment_name
  resource_group_name  = var.resource_group_name
}

data "azurerm_container_registry" "container_registry" {
  name                 = var.container_registry_name
  resource_group_name  = var.resource_group_name
}

data "azurerm_user_assigned_identity" "workload_user_assigned_identity" {
  name                = var.workload_managed_identity_name
  resource_group_name = var.resource_group_name
}

locals {
  identity = {
    type         = "UserAssigned"
    identity_ids = [data.azurerm_user_assigned_identity.workload_user_assigned_identity.id]
  }
  identity_env = {
    name         = "AZURE_CLIENT_ID"
    secret_name  = null
    value        = data.azurerm_user_assigned_identity.workload_user_assigned_identity.client_id
  }
  registry = {
    server       = data.azurerm_container_registry.container_registry.login_server
    identity     = data.azurerm_user_assigned_identity.workload_user_assigned_identity.id
  }
}

resource "azurerm_container_app" "container_app" {
  for_each                     = {for app in var.container_apps: app.name => app}

  container_app_environment_id = data.azurerm_container_app_environment.container_app_environment.id
  name                         = each.key
  resource_group_name          = var.resource_group_name
  revision_mode                = each.value.revision_mode
  tags                         = each.value.tags

  template {
    max_replicas    = each.value.template.max_replicas
    min_replicas    = each.value.template.min_replicas
    revision_suffix = each.value.template.revision_suffix

    dynamic "container" {
      for_each = each.value.template.containers

      content {
        cpu     = container.value.cpu
        image   = "${data.azurerm_container_registry.container_registry.login_server}/${container.value.image}"
        memory  = container.value.memory
        name    = container.value.name
        args    = container.value.args
        command = container.value.command

        dynamic "env" {
          for_each = container.value.env == null ? [local.identity_env] : concat(container.value.env, [local.identity_env])

          content {
            name        = env.value.name
            secret_name = env.value.secret_name
            value       = env.value.value
          }
        }

        dynamic "liveness_probe" {
          for_each = container.value.liveness_probe == null ? [] : [container.value.liveness_probe]

          content {
            port                    = liveness_probe.value.port
            transport               = liveness_probe.value.transport
            failure_count_threshold = liveness_probe.value.failure_count_threshold
            host                    = liveness_probe.value.host
            initial_delay           = liveness_probe.value.initial_delay
            interval_seconds        = liveness_probe.value.interval_seconds
            path                    = liveness_probe.value.path
            timeout                 = liveness_probe.value.timeout

            dynamic "header" {
              for_each = liveness_probe.value.header == null ? [] : [liveness_probe.value.header]

              content {
                name  = header.value.name
                value = header.value.value
              }
            }
          }
        }

        dynamic "readiness_probe" {
          for_each = container.value.readiness_probe == null ? [] : [container.value.readiness_probe]

          content {
            port                    = readiness_probe.value.port
            transport               = readiness_probe.value.transport
            failure_count_threshold = readiness_probe.value.failure_count_threshold
            host                    = readiness_probe.value.host
            interval_seconds        = readiness_probe.value.interval_seconds
            path                    = readiness_probe.value.path
            success_count_threshold = readiness_probe.value.success_count_threshold
            timeout                 = readiness_probe.value.timeout

            dynamic "header" {
              for_each = readiness_probe.value.header == null ? [] : [readiness_probe.value.header]

              content {
                name  = header.value.name
                value = header.value.value
              }
            }
          }
        }

        dynamic "startup_probe" {
          for_each = container.value.startup_probe == null ? [] : [container.value.startup_probe]

          content {
            port                    = startup_probe.value.port
            transport               = startup_probe.value.transport
            failure_count_threshold = startup_probe.value.failure_count_threshold
            host                    = startup_probe.value.host
            interval_seconds        = startup_probe.value.interval_seconds
            path                    = startup_probe.value.path
            timeout                 = startup_probe.value.timeout

            dynamic "header" {
              for_each = startup_probe.value.header == null ? [] : [startup_probe.value.header]

              content {
                name  = header.value.name
                value = header.value.name
              }
            }
          }
        }

        dynamic "volume_mounts" {
          for_each = container.value.volume_mounts == null ? [] : [container.value.volume_mounts]

          content {
            name = volume_mounts.value.name
            path = volume_mounts.value.path
          }
        }
      }
    }

    dynamic "volume" {
      for_each = each.value.template.volume == null ? [] : each.value.template.volume

      content {
        name         = volume.value.name
        storage_name = volume.value.storage_name
        storage_type = volume.value.storage_type
      }
    }
  }

  dynamic "dapr" {
    for_each = each.value.dapr == null ? [] : [each.value.dapr]

    content {
      app_id       = dapr.value.app_id
      app_port     = dapr.value.app_port
      app_protocol = dapr.value.app_protocol
    }
  }

  dynamic "identity" {
    for_each = each.value.identity == null ? [local.identity] : [each.value.identity]

    content {
      type         = identity.value.type
      identity_ids = identity.value.identity_ids
    }
  }

  dynamic "ingress" {
    for_each = each.value.ingress == null ? [] : [each.value.ingress]

    content {
      target_port                = ingress.value.target_port
      allow_insecure_connections = ingress.value.allow_insecure_connections
      external_enabled           = ingress.value.external_enabled
      transport                  = ingress.value.transport

      dynamic "traffic_weight" {
        for_each = ingress.value.traffic_weight == null ? [] : [ingress.value.traffic_weight]

        content {
          percentage      = traffic_weight.value.percentage
          label           = traffic_weight.value.label
          latest_revision = traffic_weight.value.latest_revision
          revision_suffix = traffic_weight.value.revision_suffix
        }
      }
    }
  }

  dynamic "registry" {
    for_each = each.value.registry == null ? [local.registry] : concat(each.value.registry, [local.registry])

    content {
      server   = registry.value.server
      identity = registry.value.identity
    }
  }

  dynamic "secret" {
    for_each = nonsensitive(toset([for pair in lookup(var.container_app_secrets, each.key, []) : pair.name]))

    content {
      name  = secret.key
      value = local.container_app_secrets[each.key][secret.key]
    }
  }
}