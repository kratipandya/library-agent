# Root config for the application's real infrastructure (Cosmos DB, Function
# App, Key Vault, Static Web App, App Insights — added incrementally, one
# resource type per PR). Terraform-first: no portal clicking, unlike
# infra/bootstrap/. State lives remotely in the storage account bootstrap
# created, not on any one laptop.

terraform {
  required_version = ">= 1.15"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "library-agent-rg"
    storage_account_name = "libraryagenttfstate"
    container_name       = "tfstate"
    key                  = "main.tfstate"
  }
}

provider "azurerm" {
  features {}
}

locals {
  location = "austriaeast" # only region this subscription's policy allows — see infra/bootstrap/README.md
  # Cosmos DB hit "ServiceUnavailable: high demand" in austriaeast on 2026-08-13 —
  # a capacity issue specific to that region/service, not a config or policy problem.
  # Using a different allowed region for Cosmos only; everything else stays in austriaeast.
  cosmos_location = "polandcentral"
  # Y1 (Linux Consumption) Function App plans failed with "Requested features
  # are not supported in region" in austriaeast, polandcentral, spaincentral,
  # AND italynorth — a real ARM-level probe (az rest PUT on serverfarms,
  # bypassing the CLI's flawed --sku validation) confirmed uaenorth is the
  # only one of our 5 allowed regions that actually supports Y1+Linux.
  function_app_location = "uaenorth"
}

module "resource_group" {
  source   = "../modules/resource-group"
  name     = "library-agent-app-rg"
  location = local.location
  tags = {
    project = "library-agent"
  }
}

module "cosmos" {
  source              = "../modules/cosmos"
  name                = "library-agent-cosmos"
  resource_group_name = module.resource_group.name
  location            = local.cosmos_location
  tags = {
    project = "library-agent"
  }
}

module "function_app" {
  source               = "../modules/function-app"
  name                 = "library-agent-func"
  storage_account_name = "libraryagentfuncsa"
  resource_group_name  = module.resource_group.name
  location             = local.function_app_location
  tags = {
    project = "library-agent"
  }
}
