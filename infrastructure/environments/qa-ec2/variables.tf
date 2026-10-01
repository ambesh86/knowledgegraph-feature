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

variable "subnet" {
  type    = string
  default = ""
  description = "subnet to run the infrastrucutre in, should already exist"
}

variable "vpc_id" {
  type    = string
  default = ""
  description = "vpc to run the infrastrucutre in, should already exist"
}

variable "ec2_instance_role_arn" {
  type = string
  default = ""
  description = "EC2 instance profile role"
}

variable "ec2_instance_role_name" {
  type    = string
  default = ""
  description = "instance role name for the ec2 machine"
}
