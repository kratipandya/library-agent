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
    resource_group_name = "library-agent-rg"
    storage_account_name = "libraryagenttfstate"
    container_name        = "tfstate"
    key                    = "main.tfstate"
  }
}

provider "azurerm" {
  features {}
}

locals {
  location = "austriaeast" # only region this subscription's policy allows — see infra/bootstrap/README.md
}

module "resource_group" {
  source   = "../modules/resource-group"
  name     = "library-agent-app-rg"
  location = local.location
  tags = {
    project = "library-agent"
  }
}
