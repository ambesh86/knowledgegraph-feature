# =============================================================================
# Input variables for the fresh Eugene deployment.
# Fill these in terraform.tfvars (see terraform.tfvars.example).
# =============================================================================

variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "name_prefix" {
  description = <<EOT
Prefix added to EVERY resource name. The existing prod stack uses
'eugene-search-*'. Pick something different (e.g. 'eugene-fresh',
'eugene-dev-rg') so nothing collides.
EOT
  type        = string
  default     = "eugene-fresh"
  validation {
    condition     = can(regex("^[a-z0-9-]{3,24}$", var.name_prefix))
    error_message = "name_prefix must be lowercase alphanumeric + dashes, 3..24 chars."
  }
}

# ---------------------------- Network (existing VPC) -------------------------

variable "vpc_id" {
  description = "Existing VPC ID to deploy into."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks and Neo4j EC2. At least 2 in different AZs."
  type        = list(string)
  validation {
    condition     = length(var.private_subnet_ids) >= 2
    error_message = "Provide at least 2 private subnets for HA."
  }
}

variable "public_subnet_ids" {
  description = "Subnet IDs for the ALB. Same VPC as private subnets. Use private subnets too if you want an INTERNAL ALB (recommended for CSL setup)."
  type        = list(string)
  validation {
    condition     = length(var.public_subnet_ids) >= 2
    error_message = "Provide at least 2 ALB subnets."
  }
}

variable "alb_internal" {
  description = "If true, ALB is internal (VPC-only). Matches CSL prod pattern."
  type        = bool
  default     = true
}

variable "allow_ingress_cidrs" {
  description = "CIDRs allowed to reach the ALB (e.g. your VPN range). Use [\"10.0.0.0/8\"] for VPC-wide."
  type        = list(string)
  default     = ["10.0.0.0/8"]
}

variable "alb_certificate_arn" {
  description = "ACM cert ARN for HTTPS listener. Leave empty to skip HTTPS and use HTTP only (lab mode)."
  type        = string
  default     = ""
}

# ---------------------------- Image registry ---------------------------------

variable "image_registry" {
  description = "Container registry hosting the 5 Eugene images. Examples: 'ghcr.io' or '<acct>.dkr.ecr.us-east-1.amazonaws.com'."
  type        = string
  default     = "ghcr.io"
}

variable "image_owner" {
  description = "Registry namespace. For ghcr.io it's your GitHub user/org; for ECR it's empty."
  type        = string
  default     = "aisemanticexpert"
}

variable "image_tag" {
  description = "Image tag to deploy. Pin to a sha-XXXXX tag in real production."
  type        = string
  default     = "latest"
}

variable "registry_auth_secret_arn" {
  description = "Secrets Manager ARN with registry creds (for ghcr.io private). Leave empty if pulling from ECR in the same account."
  type        = string
  default     = ""
}

# ---------------------------- Secrets ----------------------------------------

variable "openai_api_key" {
  description = "OpenAI API key (sensitive). Stored in SSM Parameter Store."
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key (optional)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "llm_provider" {
  description = "openai | anthropic | bedrock"
  type        = string
  default     = "openai"
}

variable "eugene_client_secret" {
  description = "Shared JWT signing secret across all Eugene services."
  type        = string
  sensitive   = true
}

variable "eugene_tenant_id" {
  description = "Eugene tenant ID (constant unless you fork the identity)."
  type        = string
  default     = "f8645748-68c6-4eec-bd61-c71341a6ed7d"
}

variable "eugene_client_id" {
  description = "Eugene client ID."
  type        = string
  default     = "ff58ded5-c309-4cc8-ae6a-3b7157b83879"
}

variable "agent_allowlist" {
  description = "Pipe-separated list of UPNs allowed to use the agent."
  type        = string
  default     = ""
}

variable "neo4j_password" {
  description = "Neo4j password (sensitive)."
  type        = string
  sensitive   = true
}

# ---------------------------- ECS sizing -------------------------------------

variable "service_cpu_memory" {
  description = "Fargate CPU/memory per service. Defaults are sized for moderate traffic."
  type = map(object({
    cpu    = number
    memory = number
  }))
  default = {
    eugene_ws            = { cpu = 1024, memory = 2048 }
    eugene_mcp           = { cpu = 512,  memory = 1024 }
    eugene_agent_ws      = { cpu = 1024, memory = 2048 }
    eugene_agent_ui      = { cpu = 256,  memory = 512  }
    eugene_agent_ui_next = { cpu = 256,  memory = 512  }
  }
}

variable "service_desired_count" {
  description = "Number of tasks per service."
  type = map(number)
  default = {
    eugene_ws            = 1
    eugene_mcp           = 1
    eugene_agent_ws      = 1
    eugene_agent_ui      = 1
    eugene_agent_ui_next = 1
  }
}

# ---------------------------- Neo4j EC2 --------------------------------------

variable "neo4j_instance_type" {
  description = "EC2 instance type for Neo4j."
  type        = string
  default     = "t3.large"
}

variable "neo4j_data_volume_gb" {
  description = "EBS data volume size in GB."
  type        = number
  default     = 100
}

variable "neo4j_ami_id" {
  description = "AMI ID for Neo4j EC2. Leave empty to use the latest Amazon Linux 2023 (looked up dynamically)."
  type        = string
  default     = ""
}

# ---------------------------- Tags -------------------------------------------

variable "common_tags" {
  description = "Tags applied to every resource."
  type        = map(string)
  default = {
    workload      = "eugene"
    deployment    = "fresh"
    managed_by    = "terraform"
  }
}
