# Provisions an EMPTY Azure Function App — the running platform, with no
# code deployed to it yet. Deploying agents/, api/, ingestion/ onto this is
# a separate step (CLAUDE.md Phase 4, via GitHub Actions), not this module's
# job.
#
# Flex Consumption (FC1), not the classic Y1 Dynamic plan: Y1 is blocked on
# this subscription by a zero compute quota for its VM family in every
# region that even offers Y1+Linux (verified via direct ARM probing — see
# DECISIONS.md). Flex Consumption draws from a different quota pool and is
# Azure's current-generation serverless tier for Functions anyway — still
# genuinely pay-per-execution, no idle-server cost.

# Functions needs its own storage account for internal bookkeeping (trigger
# state, logs) — unrelated to and separate from the tfstate storage account
# bootstrap created. Flex Consumption additionally needs a blob container
# inside it to hold the deployed code package.
resource "azurerm_storage_account" "functions" {
  name                     = var.storage_account_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
}

resource "azurerm_storage_container" "deployments" {
  name                  = "app-package"
  storage_account_id    = azurerm_storage_account.functions.id
  container_access_type = "private"
}

resource "azurerm_service_plan" "this" {
  name                = "${var.name}-plan"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux" # Python Functions require Linux, not Windows
  sku_name            = "FC1"
}

resource "azurerm_function_app_flex_consumption" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = azurerm_service_plan.this.id

  storage_container_type      = "blobContainer"
  storage_container_endpoint  = "${azurerm_storage_account.functions.primary_blob_endpoint}${azurerm_storage_container.deployments.name}"
  storage_authentication_type = "StorageAccountConnectionString"
  storage_access_key          = azurerm_storage_account.functions.primary_access_key

  runtime_name    = "python"
  runtime_version = "3.12" # matches .python-version / pyproject.toml requires-python

  # Hard cap on scale-out, same spirit as Cosmos's throughput cap: bounds
  # worst-case cost instead of trusting default limits (CLAUDE.md €0 target).
  maximum_instance_count = 40
  instance_memory_in_mb  = 2048

  https_only = true

  site_config {}

  tags = var.tags
}
