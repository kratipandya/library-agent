output "resource_group_name" {
  value = module.resource_group.name
}

output "location" {
  value = module.resource_group.location
}

output "cosmos_endpoint" {
  value = module.cosmos.endpoint
}
