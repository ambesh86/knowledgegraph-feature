# =============================================================================
# Provider, locals, shared data sources
# =============================================================================

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = merge(var.common_tags, { name_prefix = var.name_prefix })
  }
}

locals {
  # Image URLs derived from registry/owner/tag
  image_base = var.image_owner == "" ? var.image_registry : "${var.image_registry}/${var.image_owner}"

  images = {
    eugene_ws            = "${local.image_base}/eugene-ws:${var.image_tag}"
    eugene_mcp           = "${local.image_base}/eugene-mcp:${var.image_tag}"
    eugene_agent_ws      = "${local.image_base}/eugene-agent-ws:${var.image_tag}"
    eugene_agent_ui      = "${local.image_base}/eugene-agent-ui:${var.image_tag}"
    eugene_agent_ui_next = "${local.image_base}/eugene-agent-ui-next:${var.image_tag}"
  }

  services = ["eugene_ws", "eugene_mcp", "eugene_agent_ws", "eugene_agent_ui", "eugene_agent_ui_next"]

  # Per-service container port mapping (matches Dockerfiles in docker/)
  container_ports = {
    eugene_ws            = 8000
    eugene_mcp           = 8000
    eugene_agent_ws      = 8000
    eugene_agent_ui      = 8501
    eugene_agent_ui_next = 18502
  }

  # Per-service ALB path prefix (so one ALB serves all 5)
  path_patterns = {
    eugene_ws            = ["/api/*", "/auth/*", "/health"]
    eugene_mcp           = ["/mcp/*"]
    eugene_agent_ws      = ["/agent/api/*"]
    eugene_agent_ui      = ["/ui/*"]
    eugene_agent_ui_next = ["/*"]   # catch-all goes last in priority
  }

  alb_listener_priority = {
    eugene_ws            = 100
    eugene_mcp           = 110
    eugene_agent_ws      = 120
    eugene_agent_ui      = 130
    eugene_agent_ui_next = 1000  # catch-all
  }
}

# Latest Amazon Linux 2023 AMI for the Neo4j EC2 if user didn't pin one
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-kernel-*-x86_64"]
  }
}

data "aws_caller_identity" "current" {}
