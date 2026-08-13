# Empty Key Vault — creates the vault and its access model, but stores no
# secrets here in Terraform code. The OpenRouter key (or any secret) is set
# operationally afterward (az keyvault secret set, or the portal), not via
# `.tf` — rotating a secret shouldn't require a plan/apply, and the value
# should never need to pass through a committed file or a code review.

resource "azurerm_key_vault" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = var.tenant_id
  sku_name            = "standard"

  # RBAC over legacy access policies — the modern, recommended model; role
  # assignments (who can read/write secrets) are granted by the caller of
  # this module, not hardcoded here.
  rbac_authorization_enabled = true

  # No purge protection: a deliberate choice for this learning project,
  # where practicing `terraform destroy` matters (CLAUDE.md goal #3).
  # Paired with purge_soft_delete_on_destroy in the root provider block
  # so `destroy` doesn't leave a lingering soft-deleted vault blocking
  # the name for days. Would flip to true for anything holding real
  # production secrets.
  purge_protection_enabled = false

  tags = var.tags
}
