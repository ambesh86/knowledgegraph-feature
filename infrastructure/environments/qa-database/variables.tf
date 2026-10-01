# eugene vars
variable "aws_region" {
  type        = string
  default     = ""
  description = "AWS region"
}

variable "aws_availability_zone" {
  type        = string
  default     = ""
  description = "AWS region"
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

variable "subnets" {
  type    = set(string)
  default = []
  description = "subnet to run the infrastrucutre in, should already exist"
}

variable "vpc_id" {
  type    = string
  default = ""
  description = "vpc to run the infrastrucutre in, should already exist"
}

variable "ecs_database_cluster_name" {
  type        = string
  default     = "database-cluster"
  description = "ECS cluster to ingest and query uspto data"
}

variable "ec2_instance_role_arn" {
  type = string
  default = ""
  description = "EC2 instance profile role"
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

variable "ecs_service_role_arn" {
  type = string
  default = ""
  description = "service role arn for the ECS service"
}

variable "database_image_hash" {
  type = string
  default = "latest"
  description = "docker image hash to be used to run the ECS service"
}

