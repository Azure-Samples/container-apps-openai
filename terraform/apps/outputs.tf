output "container_app_fqdn" {
  description = "The FQDN of the Latest Revision of the Container Apps."
  value       = module.container_apps.container_app_fqdn
}