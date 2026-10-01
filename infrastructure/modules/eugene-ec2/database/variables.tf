variable "aws_region" {
  type        = string
  default     = ""
  description = "AWS region"
}

variable "aws_availability_zone" {
  type        = string
  default     = ""
  description = "AWS AZ"
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

variable "ec2_instance_role_arn" {
  type    = string
  default = ""
  description = "instance role arn for the ec2 machine"
}

variable "ec2_instance_role_name" {
  type    = string
  default = ""
  description = "instance role name for the ec2 machine"
}

variable "instance_type" {
  type    = string
  default = ""
  description = "instance type to use for the EC2 machine"
}
