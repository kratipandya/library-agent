# One Cosmos DB account, free tier — Azure allows exactly one free-tier
# account per subscription (CLAUDE.md hard constraint). free_tier_enabled
# cannot be changed after creation (forces a new resource), so this module
# starts intentionally small: the account only. The SQL database and
# containers (vectors, chat history, metadata cache) are added in a
# follow-up PR once this is reviewed and applied.

resource "azurerm_cosmosdb_account" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB" # Core (SQL) API — not Mongo/Cassandra/etc.

  free_tier_enabled = true

  consistency_policy {
    consistency_level = "Session" # per-client read-your-writes; the common default
  }

  geo_location {
    location          = var.location
    failover_priority = 0 # single region — no paid multi-region replication
  }

  # Hard cap at the free tier's 1000 RU/s: Azure rejects any attempt to
  # provision more, rather than silently billing for it (€0 target).
  capacity {
    total_throughput_limit = 1000
  }

  tags = var.tags
}
