resource_group_name            = "BlueRG"
container_app_environment_name = "BlueEnvironment"
container_registry_name        = "BlueRegistry"
workload_managed_identity_name = "BlueWorkloadIdentity"
container_apps                 = [
  {
    name                            = "chatapp"
    revision_mode                   = "Single"
    ingress                         = {
      allow_insecure_connections    = true
      external_enabled              = true
      target_port                   = 8000
      transport                     = "http"
      traffic_weight                = {
        label                       = "default"
        latest_revision             = true
        revision_suffix             = "default"
        percentage                  = 100
      }
    }
    template                        = {
      containers                    = [
        {
          name                      = "chat"
          image                     = "chat:v1"
          cpu                       = 0.5
          memory                    = "1Gi"
          env                       = [
            {
              name                  = "TEMPERATURE"
              value                 = 0.9
            },
            {
              name                  = "AZURE_OPENAI_BASE"
              value                 = "https://blueopenai.openai.azure.com/"
            },
            {
              name                  = "AZURE_OPENAI_KEY"
              value                 = ""
            },
            {
              name                  = "AZURE_OPENAI_TYPE"
              value                 = "azure_ad"
            },
            {
              name                  = "AZURE_OPENAI_VERSION"
              value                 = "2023-06-01-preview"
            },
            {
              name                  = "AZURE_OPENAI_DEPLOYMENT"
              value                 = "gpt-35-turbo-16k"
            },
            {
              name                  = "AZURE_OPENAI_MODEL"
              value                 = "gpt-35-turbo-16k"
            },
            {
              name                  = "AZURE_OPENAI_SYSTEM_MESSAGE"
              value                 = "You are a helpful assistant."
            },
            {
              name                  = "MAX_RETRIES"
              value                 = 5
            },
            {
              name                  = "BACKOFF_IN_SECONDS"
              value                 = "1"
            },
            {
              name                  = "TOKEN_REFRESH_INTERVAL"
              value                 = 2700
            }
          ]
          liveness_probe            = {
            failure_count_threshold = 3
            initial_delay           = 30
            interval_seconds        = 60
            path                    = "/"
            port                    = 8000
            timeout                 = 30
            transport               = "HTTP"
          }
          readiness_probe = {
            failure_count_threshold = 3
            interval_seconds        = 60
            path                    = "/"
            port                    = 8000
            success_count_threshold = 3
            timeout                 = 30
            transport               = "HTTP"
          }
          startup_probe = {
            failure_count_threshold = 3
            interval_seconds        = 60
            path                    = "/"
            port                    = 8000
            timeout                 = 30
            transport               = "HTTP"
          }
        }
      ]
      min_replicas                  = 1
      max_replicas                  = 3
    }
  },
  {
    name                            = "docapp"
    revision_mode                   = "Single"
    ingress                         = {
      allow_insecure_connections    = true
      external_enabled              = true
      target_port                   = 8000
      transport                     = "http"
      traffic_weight                = {
        label                       = "default"
        latest_revision             = true
        revision_suffix             = "default"
        percentage                  = 100
      }
    }
    template                        = {
      containers                    = [
        {
          name                      = "doc"
          image                     = "doc:v1"
          cpu                       = 0.5
          memory                    = "1Gi"
          env                       = [
            {
              name                  = "TEMPERATURE"
              value                 = 0.9
            },
            {
              name                  = "AZURE_OPENAI_BASE"
              value                 = "https://blueopenai.openai.azure.com/"
            },
            {
              name                  = "AZURE_OPENAI_KEY"
              value                 = ""
            },
            {
              name                  = "AZURE_OPENAI_TYPE"
              value                 = "azure_ad"
            },
            {
              name                  = "AZURE_OPENAI_VERSION"
              value                 = "2023-06-01-preview"
            },
            {
              name                  = "AZURE_OPENAI_DEPLOYMENT"
              value                 = "gpt-35-turbo-16k"
            },
            {
              name                  = "AZURE_OPENAI_MODEL"
              value                 = "gpt-35-turbo-16k"
            },
            {
              name                  = "AZURE_OPENAI_ADA_DEPLOYMENT"
              value                 = "text-embedding-ada-002"
            },
            {
              name                  = "AZURE_OPENAI_SYSTEM_MESSAGE"
              value                 = "You are a helpful assistant."
            },
            {
              name                  = "MAX_RETRIES"
              value                 = 5
            },
            {
              name                  = "CHAINLIT_MAX_FILES"
              value                 = 10
            },
            {
              name                  = "TEXT_SPLITTER_CHUNK_SIZE"
              value                 = 1000
            },
            {
              name                  = "TEXT_SPLITTER_CHUNK_OVERLAP"
              value                 = 10
            },
            {
              name                  = "EMBEDDINGS_CHUNK_SIZE"
              value                 = 16
            },
            {
              name                  = "BACKOFF_IN_SECONDS"
              value                 = "1"
            },
            {
              name                  = "CHAINLIT_MAX_SIZE_MB"
              value                 = 100
            },
            {
              name                  = "TOKEN_REFRESH_INTERVAL"
              value                 = 2700
            }
          ]
          liveness_probe = {
            failure_count_threshold = 3
            initial_delay           = 30
            interval_seconds        = 60
            path                    = "/"
            port                    = 8000
            timeout                 = 30
            transport               = "HTTP"
          }
          readiness_probe = {
            failure_count_threshold = 3
            interval_seconds        = 60
            path                    = "/"
            port                    = 8000
            success_count_threshold = 3
            timeout                 = 30
            transport               = "HTTP"
          }
          startup_probe = {
            failure_count_threshold = 3
            interval_seconds        = 60
            path                    = "/"
            port                    = 8000
            timeout                 = 30
            transport               = "HTTP"
          }
        }
      ]
      min_replicas                  = 1
      max_replicas                  = 3
    }
  }]