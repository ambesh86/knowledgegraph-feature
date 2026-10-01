# Create ECS task definition for SQS uspto application ingestion
resource "aws_ecs_task_definition" "sqs_uspto_application_ingestion_task" {
  family                = "${var.resource_prefix}-sqs-uspto-application-ingestion-task"
  cpu                    = 1024
  memory                = 2048
  network_mode           = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn      = var.uspto_ecs_role_arn

  container_definitions = jsonencode([
    {
      name      = "sqs-uspto-application-ingestion-container"
      image      = "eugene/uspto-application-ingest"
      cpu        = 1024
      memory    = 2048
      essential = true

      healthCheck = {
        command = ["CMD-SHELL", "uptime || exit 0"]
        interval = 90
        timeout = 5
        retries = 3
      }
    }
  ])

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-sqs-uspto-application-ingestion-task"
    accountType                   = var.account_type
    amsManaged                    = var.ams_managed
    amsMonitoringPolicy           = var.ams_monitoring_policy
    amsMonitoringPolicyPlatform   = var.ams_monitoring_policy_platform
    APM                           = var.apm
    businessUnit                  = var.business_unit
    costBudgetAmount              = var.cost_budget_amount
    costCenter                    = var.cost_center
    dataClassification            = var.data_classification
    patchSchedule                 = var.patch_schedule
    technicalOwner                = var.technical_owner
    workloadEnvironment           = var.workload_environment
    workloadName                  = var.workload_name
    workloadOwner                 = var.workload_owner
  }
}

# Create ECS task definition for SQS uspto pgpub ingestion
resource "aws_ecs_task_definition" "sqs_uspto_pgpub_ingestion_task" {
  family                = "${var.resource_prefix}-sqs-uspto-pgpub-ingestion-task"
  cpu                    = 1024
  memory                = 2048
  network_mode           = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn      = var.uspto_ecs_role_arn

  container_definitions = jsonencode([
    {
      name      = "${var.resource_prefix}-sqs-uspto-pgpub-ingestion-container"
      image      = "eugene/uspto-pgpub-ingest"
      cpu        = 1024
      memory    = 2048
      essential = true
    }
  ])

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-sqs-uspto-pgpub-ingestion-task"
    accountType                   = var.account_type
    amsManaged                    = var.ams_managed
    amsMonitoringPolicy           = var.ams_monitoring_policy
    amsMonitoringPolicyPlatform   = var.ams_monitoring_policy_platform
    APM                           = var.apm
    businessUnit                  = var.business_unit
    costBudgetAmount              = var.cost_budget_amount
    costCenter                    = var.cost_center
    dataClassification            = var.data_classification
    patchSchedule                 = var.patch_schedule
    technicalOwner                = var.technical_owner
    workloadEnvironment           = var.workload_environment
    workloadName                  = var.workload_name
    workloadOwner                 = var.workload_owner
  }
}

resource "aws_ecs_service" "sqs_uspto_application_ingestion_service" {
  name            = "${var.resource_prefix}-sqs-uspto-application-ingestion-service"
  cluster         = var.ecs_uspto_cluster_name
  task_definition = aws_ecs_task_definition.sqs_uspto_application_ingestion_task.arn
  desired_count   = 1
  launch_type      = "FARGATE"

  for_each = toset([for s in data.aws_subnet.uspto_subnets : s.id])
  network_configuration {
    security_groups  = [aws_security_group.allow_outbound.id]
    subnets          = toset([each.value])
    assign_public_ip = false
  }

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-sqs-uspto-application-ingestion-service"
    accountType                   = var.account_type
    amsManaged                    = var.ams_managed
    amsMonitoringPolicy           = var.ams_monitoring_policy
    amsMonitoringPolicyPlatform   = var.ams_monitoring_policy_platform
    APM                           = var.apm
    businessUnit                  = var.business_unit
    costBudgetAmount              = var.cost_budget_amount
    costCenter                    = var.cost_center
    dataClassification            = var.data_classification
    patchSchedule                 = var.patch_schedule
    technicalOwner                = var.technical_owner
    workloadEnvironment           = var.workload_environment
    workloadName                  = var.workload_name
    workloadOwner                 = var.workload_owner
  }
}

resource "aws_ecs_service" "sqs_uspto_pgpub_ingestion_service" {
  name            = "${var.resource_prefix}-sqs-uspto-pgpub-ingestion-service"
  cluster         = var.ecs_uspto_cluster_name
  task_definition = aws_ecs_task_definition.sqs_uspto_pgpub_ingestion_task.arn
  desired_count   = 1
  launch_type      = "FARGATE"

  for_each = toset([for s in data.aws_subnet.uspto_subnets : s.id])
  network_configuration {
    security_groups  = [aws_security_group.allow_outbound.id]
    subnets          = toset([each.value])
    assign_public_ip = false
  }

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-sqs-uspto-pgpub-ingestion-service"
    accountType                   = var.account_type
    amsManaged                    = var.ams_managed
    amsMonitoringPolicy           = var.ams_monitoring_policy
    amsMonitoringPolicyPlatform   = var.ams_monitoring_policy_platform
    APM                           = var.apm
    businessUnit                  = var.business_unit
    costBudgetAmount              = var.cost_budget_amount
    costCenter                    = var.cost_center
    dataClassification            = var.data_classification
    patchSchedule                 = var.patch_schedule
    technicalOwner                = var.technical_owner
    workloadEnvironment           = var.workload_environment
    workloadName                  = var.workload_name
    workloadOwner                 = var.workload_owner
  }
}

