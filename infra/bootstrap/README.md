# Bootstrap module

Creates the storage account other Terraform modules use as a remote backend.
Kept as its own module with **local state** — it can't store its own state in
the backend it's responsible for creating.

The resource group, storage account, and container were created by hand
first (portal + CLI — see `docs/DECISIONS.md` entry 005 for why CLI was
needed for the storage account), then brought under management here with
`terraform import`, so the resources existed and were inspected before any
`.tf` code described them (CLAUDE.md learning goal #3).

## Commands used (for reference / reruns on a fresh machine)

```bash
cd infra/bootstrap
terraform init

terraform import azurerm_resource_group.tfstate \
  /subscriptions/<sub-id>/resourceGroups/library-agent-rg

terraform import azurerm_storage_account.tfstate \
  /subscriptions/<sub-id>/resourceGroups/library-agent-rg/providers/Microsoft.Storage/storageAccounts/libraryagenttfstate

terraform import azurerm_storage_container.tfstate \
  /subscriptions/<sub-id>/resourceGroups/library-agent-rg/providers/Microsoft.Storage/storageAccounts/libraryagenttfstate/blobServices/default/containers/tfstate

terraform plan   # should show "No changes" once main.tf matches reality
```

Find `<sub-id>` with `az account show --query id -o tsv`.

## Region note

Azure for Students subscriptions carry a region allowlist (subscription
policy, not documented — found via `az policy assignment list`). As of
2026-08-12 the allowed regions are: `austriaeast`, `polandcentral`,
`uaenorth`, `spaincentral`, `italynorth`. Every real resource in this
project uses `austriaeast`.
