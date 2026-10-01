variable "dotenv" {
  type        = map
  default     = {}
  description = "dotenv environment variables to pass into the AWS compute"
  sensitive = true
}

variable "uspto_env" {
  type        = map
  default     = {}
  description = "secrets environment variables to pass into the AWS compute"
}

variable "base_tags" {
  type    = map
  default = {}
  description = "base tags to apply to resources"
}

variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region"
}

variable "ecs_uspto_cluster_arn" {
  type        = string
  default     = "uspto-cluster"
  description = "ECS cluster to ingest and query uspto data"
}

variable "ecs_uspto_cluster_name" {
  type        = string
  default     = "uspto-cluster"
  description = "ECS cluster to ingest and query uspto data"
}

variable "uspto_ecs_task_execution_role_arn" {
  type        = string
  default     = ""
  description = "IAM role to execute an ECS task"
}

variable "uspto_ecs_task_role_arn" {
  type        = string
  default     = ""
  description = "IAM role to run ECS task"
}

variable "uspto_event_bridge_role_arn" {
  type        = string
  default     = ""
  description = "IAM role to run a ECS task from an event bridge timer"
}

variable "subnets" {
  type    = set(string)
  default = [""]
  description = "subnet to run the uspto infrastructure in, should already exist"
}

variable "vpc_id" {
  type    = string
  default = ""
  description = "vpc to run the uspto infrastructure in, should already exist"
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
  default     = "d1"
  description = "d1 for development, p1 for prod"
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

