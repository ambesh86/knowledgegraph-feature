variable "aws_region" {
  type        = string
  default     = ""
  description = "AWS region"
}

variable "subnets" {
  type    = set(string)
  default = []
  description = "subnet to run the infrastructure within"
}

variable "vpc_id" {
  type    = string
  default = ""
  description = "vpc to run the infrastructure within"
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

variable "logs_bucket" {
  type = string
  default = ""
  description = "s3 bucket to hold logs for the load balancer"
}

variable "base_tags" {
  type    = map
  default = {}
  description = "base tags to apply to resources"
}
