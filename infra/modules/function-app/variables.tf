variable "name" {
  description = "Function App name (globally unique — gets a *.azurewebsites.net hostname)"
  type        = string
}

variable "storage_account_name" {
  description = "Name for the Function App's own storage account (bookkeeping only — separate from tfstate storage)"
  type        = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
