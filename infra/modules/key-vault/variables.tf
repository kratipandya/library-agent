variable "name" {
  description = "Key Vault name (globally unique)"
  type        = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "tenant_id" {
  description = "Azure AD tenant ID for authenticating requests to this vault"
  type        = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
