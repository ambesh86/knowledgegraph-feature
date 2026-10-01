variable "aws_region" {
  type        = string
  default     = ""
  description = "AWS region"
}

variable "subnets" {
  type    = set(string)
  default = [
    # us-east-1a
    "subnet-0387dd9353f3f91b7",
    # us-east-1b
    "subnet-07bd7b53c61cdd153"
  ]
  description = "subnet to run the infrastructure within"
}

variable "vpc_id" {
  type    = string
  default = "vpc-070f89d8985cafbb6"
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