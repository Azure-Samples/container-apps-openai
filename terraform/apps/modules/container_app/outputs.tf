output "container_app_fqdn" {
  description = "The FQDN of the Latest Revision of the Container App."
  value       = { for name, container_app in azurerm_container_app.container_app : name => "https://${container_app.latest_revision_fqdn}" }
}