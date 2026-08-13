output "resource_group_name" {
  value = module.resource_group.name
}

output "location" {
  value = module.resource_group.location
}

output "cosmos_endpoint" {
  value = module.cosmos.endpoint
}

output "function_app_hostname" {
  value = module.function_app.default_hostname
}

output "key_vault_uri" {
  value = module.key_vault.vault_uri
}
