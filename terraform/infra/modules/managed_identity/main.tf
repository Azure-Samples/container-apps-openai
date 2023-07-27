resource "azurerm_user_assigned_identity" "workload_user_assigned_identity" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  lifecycle {
    ignore_changes = [
      tags
    ]
  }
}

resource "azurerm_role_assignment" "cognitive_services_user_assignment" {
  scope                = var.openai_id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.workload_user_assigned_identity.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "acr_pull_assignment" {
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.workload_user_assigned_identity.principal_id
  skip_service_principal_aad_check = true
}