terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.10.0"

  backend "s3" {
    # refer to 
    # 1- ./global.s3.backend.hcl and 
    # 2- <<env.>.s3.backend.hcl based on the deployment environment
  }
}

locals {
  aws_deployment_region = "eu-central-1"
  workload_description  = "AI & Automation - scop experiment"
  common_tags = {
    workloadName        = "scop"
    workloadOwner       = "AI and Automation"
    workloadEnvironment = "q1"
    costCenter          = "AI and Automation"
    businessUnit        = "AI and Automation"
    costBudgetAmount    = 1000
    dataClassification  = "business-use" # one of public, business-use, confidential, restricted-confidential
  }
  system_name="eugene"
  service_type="webservice"
}

provider "aws" {
  region = local.aws_deployment_region
  alias  = "application"
}

resource "aws_servicecatalogappregistry_application" "default" {
  provider    = aws.application
  name        = "${local.common_tags.workloadName}-${local.system_name}-${local.service_type}-${local.common_tags.workloadEnvironment}"
  description = local.workload_description
  tags = {
    workloadName        = local.common_tags.workloadName
    workloadEnvironment = local.common_tags.workloadEnvironment
  }
}

provider "aws" {
  region = "eu-central-1"
  default_tags {
    tags = merge(
      local.common_tags,
      aws_servicecatalogappregistry_application.default.application_tag
    )
  }
}
