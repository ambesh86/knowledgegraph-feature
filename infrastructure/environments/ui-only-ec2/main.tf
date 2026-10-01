provider "aws" {
  region = var.aws_region
  # The CSL org enforces a mandatory-tagging SCP (DenyWorkloadName/DenyCC/...)
  # that DENIES ec2:RunInstances unless these governance tags are present ON THE
  # REQUEST. default_tags propagates them into the RunInstances TagSpecification
  # for both the instance and its EBS volume (the SCP guards instance/* + volume/*).
  # Values mirror the known-compliant Eugene backend box (euGENE-1 / i-0c7835e...).
  default_tags {
    tags = merge(var.common_tags, var.governance_tags, { name_prefix = var.name_prefix })
  }
}

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-kernel-*-x86_64"]
  }
}

data "aws_caller_identity" "current" {}

locals {
  ami_id         = var.ami_id == "" ? data.aws_ami.al2023.id : var.ami_id
  use_ghcr_login = var.ghcr_username_ssm_arn != "" && var.ghcr_token_ssm_arn != ""
}
