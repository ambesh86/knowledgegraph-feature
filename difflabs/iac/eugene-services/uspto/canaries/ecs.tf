# Create ECS task definition for web service
# WARN: if this is a private vpc you may need to setup endpoints
# TODO: setup endpoint automatically
# https://repost.aws/knowledge-center/ecs-fargate-pull-container-error
resource "aws_ecs_task_definition" "api_canaries_task" {
  family                 = "${var.resource_prefix}-eugene-api-canaries-task"
  cpu                    = 512
  memory                 = 1024
  network_mode           = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn      = var.uspto_ecs_task_execution_role_arn
  task_role_arn           = var.uspto_ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name      = "api_canaries"
      image     = local.api_canaries_image
      cpu       = 512
      memory    = 1024
      essential = true

      restartPolicy = {
        enabled = true
        # Prevent container restart on a successful exit code
        ignoredExitCodes = [0]
        # How long the container must run successfully before a restart is attempted
        restartAttemptPeriod = 120
      }

      logConfiguration = {
        logDriver = "awslogs"
        options   = {
            "awslogs-group"         = aws_cloudwatch_log_group.api_canaries_log_group.name
            "awslogs-region"        = var.aws_region
            "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command = ["CMD-SHELL", "date || exit 0"]
        interval = 15
        timeout  = 5
        retries  = 3
      }

      environment = [
        # WARN: verify, this pull behavior may not refresh the service as expected
        # may need to force new deployment e.g.
        # aws ecs update-service --cluster stage-eugene-uspto-cluster --service stage-eugene-api-canaries --force-new-deployment
        {
          name  = "ECS_IMAGE_PULL_BEHAVIOR"
          value = var.dotenv.ECS_IMAGE_PULL_BEHAVIOR
        }
      ]
    }
  ])

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-api-canaries-task"
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
  })
}
