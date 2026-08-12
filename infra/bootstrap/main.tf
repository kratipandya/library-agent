# Bootstrap module — creates the storage backend that every other Terraform
# module will use for its remote state. This module's own state stays LOCAL
# (terraform.tfstate on disk, gitignored): it can't use the backend it creates
# to store itself. Applied once, touched rarely.
#
# Resources here were created by hand in the Azure portal / CLI first, then
# brought under Terraform with `terraform import` — see README.md in this
# directory for the exact commands and why (CLAUDE.md learning goal #3).

terraform {
  required_version = ">= 1.15"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Azure for Students subscriptions carry a region-allowlist policy; only
# these regions accept new resources (checked 2026-08-12 via
# `az policy assignment list`). Austria East is the closest to home.
resource "azurerm_resource_group" "tfstate" {
  name     = "library-agent-rg"
  location = "westeurope" # unchanged from manual creation — RG location is
  # just deployment metadata, not a constraint on resources inside it.
}

resource "azurerm_storage_account" "tfstate" {
  name                     = "libraryagenttfstate"
  resource_group_name      = azurerm_resource_group.tfstate.name
  location                 = "austriaeast"
  account_tier             = "Standard"
  account_replication_type = "LRS"
  # Explicit, not relying on the provider default: the CLI created this
  # account with the deprecated TLS 1.0 floor (no flag was passed); we
  # want 1.2 going forward. `terraform apply` will tighten this on Azure.
  min_tls_version = "TLS1_2"
}

resource "azurerm_storage_container" "tfstate" {
  name                  = "tfstate"
  storage_account_id    = azurerm_storage_account.tfstate.id
  container_access_type = "private"
}
