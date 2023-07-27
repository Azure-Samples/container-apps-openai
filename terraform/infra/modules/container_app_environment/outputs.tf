output "name" {
  value       = azurerm_container_app_environment.container_app_environment.name
  description = "Specifies the name of the Azure Container Apps Environment."
}

output "id" {
  value       = azurerm_container_app_environment.container_app_environment.id
  description = "Specifies the resource id of the Azure Container Apps Environment."
}