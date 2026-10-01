variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region"
}

variable "ecs_uspto_cluster_name" {
  type        = string
  default     = "uspto-cluster"
  description = "ECS cluster to ingest and query uspto data"
}

variable "ecs_database_cluster_name" {
  type        = string
  default     = "database-cluster"
  description = "ECS cluster to ingest and query uspto data"
}

variable "sqs_uspto_application_queue_name" {
  type        = string
  default     = "uspto-application-queue"
  description = "SQS queue to ingest united states patent (uspto) application metadata documents"
}

variable "sqs_uspto_pgpub_queue_name" {
  type        = string
  default     = "uspto-pgpub-queue"
  description = "SQS queue to ingest united states patent (uspto) pregrant publication documents"
}

variable "subnets" {
  type    = set(string)
  default = [
    # us-east-1a
    "subnet-0387dd9353f3f91b7",
    # "subnet-056b148d750529cc3",
    # "subnet-0241ee86c0f81af89",
    # "subnet-0999c03593fa6a17b",
    # us-east-1b
    "subnet-07bd7b53c61cdd153"
    # "subnet-0e5e397dcc26b69ce"
  ]
  description = "subnet to run the uspto infrastrucutre in, should already exist"
}

variable "vpc_id" {
  type    = string
  default = "vpc-070f89d8985cafbb6"
  description = "vpc to run the uspto infrastrucutre in, should already exist"
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

