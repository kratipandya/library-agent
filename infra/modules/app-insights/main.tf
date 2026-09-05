# Workspace-based Application Insights — the modern, currently-recommended
# shape. The standalone "classic" App Insights resource (no workspace_id) is
# being phased out by Microsoft; all telemetry actually lands in the Log
# Analytics Workspace, with App Insights as the query/UX layer on top.
#
# Both layers get an explicit daily ingestion cap — same €0-safety
# philosophy as Cosmos's RU/s cap and the Function App's instance-count
# cap. Azure Monitor's free grant is 5 GB/month; capping at 1 GB/day means
# even a full month of sustained logging can't quietly exceed it.

resource "azurerm_log_analytics_workspace" "this" {
  name                = "${var.name}-logs"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  daily_quota_gb      = 1

  tags = var.tags
}

resource "azurerm_application_insights" "this" {
  name                 = var.name
  resource_group_name  = var.resource_group_name
  location             = var.location
  workspace_id         = azurerm_log_analytics_workspace.this.id
  application_type     = "web" # HTTP-facing service (the orchestrator's /chat endpoint)
  daily_data_cap_in_gb = 1     # defaults to 100 — far more than this project needs

  tags = var.tags
}
