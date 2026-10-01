# =============================================================================
# ECS Fargate cluster, task definitions, services, IAM, log groups
# =============================================================================

resource "aws_ecs_cluster" "main" {
  name = "${var.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# One CloudWatch log group per service
resource "aws_cloudwatch_log_group" "svc" {
  for_each          = toset(local.services)
  name              = "/ecs/${var.name_prefix}/${each.value}"
  retention_in_days = 14
}

# ---------- IAM ---------------------------------------------------------------

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "task_execution" {
  name               = "${var.name_prefix}-task-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "task_execution_managed" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Allow execution role to read SSM SecureString params for this prefix.
resource "aws_iam_role_policy" "task_execution_ssm" {
  name = "${var.name_prefix}-task-execution-ssm"
  role = aws_iam_role.task_execution.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect   = "Allow",
      Action   = ["ssm:GetParameters", "kms:Decrypt"],
      Resource = [
        "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.name_prefix}/*",
        "*"
      ]
    }]
  })
}

# Task role — what the running container can do. Minimal: bedrock invoke only.
resource "aws_iam_role" "task" {
  name               = "${var.name_prefix}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy" "task_bedrock" {
  count = var.llm_provider == "bedrock" ? 1 : 0
  name  = "${var.name_prefix}-task-bedrock"
  role  = aws_iam_role.task.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect   = "Allow",
      Action   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      Resource = "*"
    }]
  })
}

# ---------- Per-service container env -----------------------------------------
# Common env constants shared by all backend services.
locals {
  common_env = [
    { name = "ENVIRONMENT",         value = "production" },
    { name = "EUGENE_TENANT_ID",    value = var.eugene_tenant_id },
    { name = "EUGENE_CLIENT_ID",    value = var.eugene_client_id },
    { name = "EUGENE_ISSUER",       value = "https://eugene.ai.cslg1.cslg.net/${var.eugene_tenant_id}" },
    { name = "EUGENE_AUDIENCE",     value = "api://eugene/${var.eugene_client_id}" },
    { name = "AWS_REGION",          value = var.aws_region },
  ]

  common_secrets = [
    { name = "EUGENE_CLIENT_SECRET", valueFrom = aws_ssm_parameter.eugene_client_secret.arn },
  ]

  # Service-specific environment
  service_env = {
    eugene_ws = concat(local.common_env, [
      { name = "NEO4J_URI",      value = "bolt://${aws_instance.neo4j.private_ip}:7687" },
      { name = "NEO4J_USERNAME", value = "neo4j" },
      { name = "ENTRA_CLIENT_ID",     value = "not-used" },
      { name = "ENTRA_CLIENT_SECRET", value = "not-used" },
      { name = "ENTRA_TENANT_ID",     value = "not-used" },
      { name = "ENTRA_AUTHORITY",     value = "https://login.microsoftonline.com/not-used" },
      { name = "ENTRA_SCOPE",         value = "email" },
      { name = "REDIRECT_URI",        value = "https://${aws_lb.main.dns_name}/auth/callback" },
      { name = "REDIRECT_PATH",       value = "/auth/callback" },
    ])

    eugene_mcp = concat(local.common_env, [
      { name = "EUGENE_API_BASE", value = "http://${var.name_prefix}-eugene-ws.local:8000" },
    ])

    eugene_agent_ws = concat(local.common_env, [
      { name = "EUGENE_MCP_SERVER_URL",        value = "http://${var.name_prefix}-eugene-mcp.local:8000/mcp" },
      { name = "LLM_PROVIDER",                 value = var.llm_provider },
      { name = "EUGENE_AGENT_ALLOWLIST",       value = var.agent_allowlist },
      { name = "EUGENE_AGENT_MAX_ITERATIONS",  value = "20" },
      { name = "EUGENE_AGENT_STREAM_TIMEOUT_S",value = "180" },
      { name = "EUGENE_MAX_TOOL_CALLS",        value = "25" },
    ])

    eugene_agent_ui = [
      { name = "EUGENE_AGENT_API_URL", value = "http://${var.name_prefix}-eugene-agent-ws.local:8000/agent/api/query/stream" },
    ]

    eugene_agent_ui_next = [
      { name = "NODE_ENV",              value = "production" },
      { name = "EUGENE_CORE_API_URL",   value = "http://${var.name_prefix}-eugene-ws.local:8000" },
      { name = "EUGENE_AGENT_API_URL",  value = "http://${var.name_prefix}-eugene-agent-ws.local:8000/agent/api" },
    ]
  }

  service_secrets = {
    eugene_ws = concat(local.common_secrets, [
      { name = "NEO4J_PASSWORD", valueFrom = aws_ssm_parameter.neo4j_password.arn },
    ])
    eugene_mcp      = local.common_secrets
    eugene_agent_ws = concat(local.common_secrets, [
      { name = "OPENAI_API_KEY", valueFrom = aws_ssm_parameter.openai_key.arn },
    ], var.anthropic_api_key == "" ? [] : [
      { name = "ANTHROPIC_API_KEY", valueFrom = aws_ssm_parameter.anthropic_key[0].arn },
    ])
    eugene_agent_ui      = []
    eugene_agent_ui_next = []
  }
}

# ---------- Service-discovery namespace (so services find each other) -------

resource "aws_service_discovery_private_dns_namespace" "this" {
  name = "${var.name_prefix}.local"
  vpc  = var.vpc_id
}

resource "aws_service_discovery_service" "svc" {
  for_each = toset(local.services)
  name     = "${var.name_prefix}-${replace(each.value, "_", "-")}"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.this.id
    dns_records {
      ttl  = 10
      type = "A"
    }
    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

# ---------- Task definitions -------------------------------------------------

resource "aws_ecs_task_definition" "svc" {
  for_each                 = toset(local.services)
  family                   = "${var.name_prefix}-${each.value}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.service_cpu_memory[each.value].cpu
  memory                   = var.service_cpu_memory[each.value].memory
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = each.value
    image     = local.images[each.value]
    essential = true
    portMappings = [{
      containerPort = local.container_ports[each.value]
      protocol      = "tcp"
    }]
    environment = local.service_env[each.value]
    secrets     = local.service_secrets[each.value]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.svc[each.value].name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = each.value
      }
    }
    repositoryCredentials = var.registry_auth_secret_arn == "" ? null : {
      credentialsParameter = var.registry_auth_secret_arn
    }
  }])
}

# ---------- ECS services -----------------------------------------------------

resource "aws_ecs_service" "svc" {
  for_each        = toset(local.services)
  name            = "${var.name_prefix}-${each.value}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.svc[each.value].arn
  desired_count   = var.service_desired_count[each.value]
  launch_type     = "FARGATE"
  propagate_tags  = "SERVICE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.svc[each.value].arn
    container_name   = each.value
    container_port   = local.container_ports[each.value]
  }

  service_registries {
    registry_arn = aws_service_discovery_service.svc[each.value].arn
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  depends_on = [
    aws_lb_listener.http,
    aws_lb_listener.https,
    aws_instance.neo4j,
  ]
}
