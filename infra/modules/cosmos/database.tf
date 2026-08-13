# One SQL database with shared (database-level) throughput, so the three
# containers below don't each need their own 400 RU/s minimum — that would
# require 1200 RU/s for three containers and blow past the account's
# 1000 RU/s cap. Containers below intentionally omit `throughput` so they
# draw from this shared pool.
#
# Vector-search-specific indexing (for the Content agent's CosmosVectorStore,
# Phase 4) is deliberately not configured yet — containers exist now,
# indexing policy tuning happens when that code is written.

resource "azurerm_cosmosdb_sql_database" "library" {
  name                = "library"
  resource_group_name = azurerm_cosmosdb_account.this.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  throughput          = 400
}

resource "azurerm_cosmosdb_sql_container" "vectors" {
  name                = "vectors"
  resource_group_name = azurerm_cosmosdb_account.this.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  database_name       = azurerm_cosmosdb_sql_database.library.name
  partition_key_paths = ["/book_id"] # ~20 books — even spread, matches Content agent's book_title filter
}

resource "azurerm_cosmosdb_sql_container" "chat_history" {
  name                = "chat_history"
  resource_group_name = azurerm_cosmosdb_account.this.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  database_name       = azurerm_cosmosdb_sql_database.library.name
  partition_key_paths = ["/session_id"] # matches api/app.py's session_id keying
}

resource "azurerm_cosmosdb_sql_container" "metadata_cache" {
  name                = "metadata_cache"
  resource_group_name = azurerm_cosmosdb_account.this.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  database_name       = azurerm_cosmosdb_sql_database.library.name
  partition_key_paths = ["/id"] # cached Open Library lookups, keyed by work_key
}
