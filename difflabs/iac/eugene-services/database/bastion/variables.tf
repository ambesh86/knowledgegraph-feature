variable "dotenv" {
  type        = map
  default     = {}
  description = "dotenv environment variables to pass into the AWS compute"
  sensitive = true
}

variable "database_env" {
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

variable "ecs_database_cluster_name" {
  type        = string
  default     = "eugene-database-cluster"
  description = "ECS cluster to host euGENE database"
}

variable "bastion_ecs_task_role_arn" {
  type        = string
  default     = ""
  description = "IAM role to run a ECS task"
}

variable "bastion_ecs_service_role_arn" {
  type        = string
  default     = ""
  description = "IAM role to run a ECS service"
}

variable "subnets" {
  type    = set(string)
  default = [""]
  description = "subnet to run the eugene database infrastrucutre in, should already exist"
}

variable "vpc_id" {
  type    = string
  default = ""
  description = "vpc to run the eugene database infrastrucutre in, should already exist"
}

variable "workload_name" {
  type    = string
  default = ""
  description = "workload tag needed for ai accelerator"
}

variable "resource_prefix" {
  type    = string
  default = "dev"
  description = "prefix for ai accelerator resources"
}

