# =============================================================================
# Security groups and SSM Parameter Store secrets
# =============================================================================

# ---------- Security groups --------------------------------------------------

resource "aws_security_group" "alb" {
  name        = "${var.name_prefix}-alb-sg"
  description = "Eugene ALB ingress"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTPS from allowed CIDRs"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allow_ingress_cidrs
  }

  ingress {
    description = "HTTP from allowed CIDRs (also serves no-TLS lab mode)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allow_ingress_cidrs
  }

  egress {
    description = "all egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "ecs_tasks" {
  name        = "${var.name_prefix}-ecs-tasks-sg"
  description = "Eugene ECS task SG: ALB → tasks, tasks → Neo4j, tasks → internet"
  vpc_id      = var.vpc_id

  ingress {
    description     = "from ALB"
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description = "intra-cluster (tasks talk to each other)"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    self        = true
  }

  egress {
    description = "all egress (LLM APIs, registry, Neo4j)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "neo4j" {
  name        = "${var.name_prefix}-neo4j-sg"
  description = "Eugene Neo4j EC2: bolt + browser from ECS only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Bolt from ECS tasks"
    from_port       = 7687
    to_port         = 7687
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  ingress {
    description     = "Neo4j Browser HTTP from ECS tasks"
    from_port       = 7474
    to_port         = 7474
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---------- Secrets (SSM Parameter Store, SecureString) ----------------------
# We use SSM (cheaper than Secrets Manager) since these are static.
# Rotating? Switch to aws_secretsmanager_secret.

resource "aws_ssm_parameter" "openai_key" {
  name        = "/${var.name_prefix}/OPENAI_API_KEY"
  description = "OpenAI API key for Eugene"
  type        = "SecureString"
  value       = var.openai_api_key
  overwrite   = true
}

resource "aws_ssm_parameter" "anthropic_key" {
  count       = var.anthropic_api_key == "" ? 0 : 1
  name        = "/${var.name_prefix}/ANTHROPIC_API_KEY"
  description = "Anthropic API key for Eugene"
  type        = "SecureString"
  value       = var.anthropic_api_key
  overwrite   = true
}

resource "aws_ssm_parameter" "eugene_client_secret" {
  name        = "/${var.name_prefix}/EUGENE_CLIENT_SECRET"
  description = "Eugene JWT signing secret"
  type        = "SecureString"
  value       = var.eugene_client_secret
  overwrite   = true
}

resource "aws_ssm_parameter" "neo4j_password" {
  name        = "/${var.name_prefix}/NEO4J_PASSWORD"
  description = "Neo4j password"
  type        = "SecureString"
  value       = var.neo4j_password
  overwrite   = true
}
