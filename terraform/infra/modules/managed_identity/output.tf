output "id" {
  value = azurerm_user_assigned_identity.workload_user_assigned_identity.id
  description = "Specifies the resource id of the workload user-defined managed identity"
}

output "location" {
  value = azurerm_user_assigned_identity.workload_user_assigned_identity.location
  description = "Specifies the location of the workload user-defined managed identity"
}

output "name" {
  value = azurerm_user_assigned_identity.workload_user_assigned_identity.name
  description = "Specifies the name of the workload user-defined managed identity"
}
