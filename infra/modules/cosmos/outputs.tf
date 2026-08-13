output "account_name" {
  value = azurerm_cosmosdb_account.this.name
}

output "endpoint" {
  value = azurerm_cosmosdb_account.this.endpoint
}

output "id" {
  value = azurerm_cosmosdb_account.this.id
}

output "database_name" {
  value = azurerm_cosmosdb_sql_database.library.name
}

output "container_names" {
  value = {
    vectors        = azurerm_cosmosdb_sql_container.vectors.name
    chat_history   = azurerm_cosmosdb_sql_container.chat_history.name
    metadata_cache = azurerm_cosmosdb_sql_container.metadata_cache.name
  }
}
