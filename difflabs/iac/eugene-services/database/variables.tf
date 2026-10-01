variable "dotenv" {
  type        = map
  default     = {}
  description = "dotenv environment variables to pass into the AWS compute"
}

variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region"
}

variable "aws_account_id" {
  type        = string
  default     = ""
  description = "AWS account id"
}

variable "ecs_database_cluster_name" {
  type        = string
  default     = "database-cluster"
  description = "ECS cluster to ingest and query database data"
}

variable "subnets" {
  type    = set(string)
  default = [""]
  description = "subnet to run the database infrastrucutre in, should already exist"
}

variable "vpc_id" {
  type    = string
  default = ""
  description = "vpc to run the database infrastrucutre in, should already exist"
}

variable "workload_name" {
  type    = string
  default = ""
  description = "workload tag needed for ai accelerator"
}

variable "resource_prefix" {
  type    = string
  default = ""
  description = "prefix for ai accelerator resources"
}

