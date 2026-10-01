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

variable "ecs_uspto_cluster_name" {
  type        = string
  default     = "uspto-cluster"
  description = "ECS cluster to ingest and query uspto data"
}

variable "uspto_ecs_role_arn" {
  type        = string
  default     = ""
  description = "IAM role to run a ECS task"
}

variable "subnets" {
  type    = set(string)
  default = [""]
  description = "subnet to run the uspto infrastrucutre in, should already exist"
}

variable "vpc_id" {
  type    = string
  default = ""
  description = "vpc to run the uspto infrastrucutre in, should already exist"
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

variable "ecs_execution_role_arn" {
  type = string
  default = ""
  description = "execution role arn for the ECS task"
}

variable "ecs_task_role_arn" {
  type = string
  default = ""
  description = "task role arn for the ECS task"
}

variable "image_hash" {
  type = string
  default = "latest"
  description = "docker image hash to be used to run the ECS service"
}
