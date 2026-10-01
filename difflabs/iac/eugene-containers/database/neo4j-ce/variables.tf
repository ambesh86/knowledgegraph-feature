variable "base_tags" {
  type    = map
  default = {}
  description = "base tags to apply to resources"
}

variable "resource_prefix" {
  type    = string
  default = ""
  description = "prefix for ai accelerator resources"
}

variable "apm" {
  type    = string
  default = ""
  description = "Application Portfolio Management Number"
}

variable "workload_name" {
  type    = string
  default = ""
  description = ""
}

variable "workload_owner" {
  type        = string
  default     = ""
  description = "Email of the workload owner"
}

variable "technical_owner" {
  type        = string
  default     = ""
  description = "Email of the technical owner"
}

variable "workload_environment" {
  type        = string
  default     = "d1 for development, p1 for prod"
  description = ""
}

variable "cost_center" {
  type        = number
  default     = 4520450000
  description = "10 digit cost center number"
}

variable "business_unit" {
  type        = string
  default     = "Information and Technology"
}

variable "data_classification" {
  type        = string
  default     = ""
}

variable "ams_monitoring_policy_platform" {
  type        = string
  default     = "ams-monitored-linux"
}

variable "ams_monitoring_policy" {
  type        = string
  default     = "ams-monitored"
}

variable "ams_managed" {
  type        = bool
  default     = false
}

variable "cost_budget_amount" {
  type        = number
  default     = 0
}

variable "patch_schedule" {
  type        = string
  default     = ""
}

variable "account_type" {
  type        = string
  default     = ""
}