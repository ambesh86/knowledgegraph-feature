variable "aws_region" {
  type        = string
  default     = ""
  description = "AWS region"
}

variable "subnet" {
  type    = string
  default = ""
  description = "subnet to run the eugene database within, should already exist"
}

variable "vpc_id" {
  type    = string
  default = ""
  description = "vpc to run the eugene database within, should already exist"
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

