# Create ECS task definition for web service
# WARN: if this is a private vpc you may need to setup endpoints
# TODO: setup endpoint automatically
# https://repost.aws/knowledge-center/ecs-fargate-pull-container-error
resource "aws_ecs_task_definition" "web_service_search_task" {
  family                = "${var.resource_prefix}-eugene-search-ws-task"
  cpu                    = 1024
  memory                = 2048
  network_mode           = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn      = var.uspto_ecs_task_execution_role_arn
  task_role_arn           = var.uspto_ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name      = "search_ws"
      image      = local.search_ws_image
      cpu        = 1024
      memory    = 2048
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol       = "tcp"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options   = {
            "awslogs-group"         = aws_cloudwatch_log_group.search_web_service_log_group.name
            "awslogs-region"        = var.aws_region
            "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command = ["CMD-SHELL", "date || exit 0"]
        interval = 90
        timeout = 5
        retries = 3
      }

      environment = [
        # huggingface params
        {
          name  = "HF_HUB_OFFLINE"
          value = var.dotenv.HF_HUB_OFFLINE
        },
        {
          name  = "HF_HUB_CACHE"
          value = var.dotenv.HF_HUB_CACHE
        },
        # end huggingface params
        # WARN: verify, this pull behavior may not refresh the service as expected
        # may need to force new deployment e.g.
        # aws ecs update-service --cluster stage-eugene-uspto-cluster --service stage-eugene-search-ws --force-new-deployment
        {
          name  = "ECS_IMAGE_PULL_BEHAVIOR"
          value = var.dotenv.ECS_IMAGE_PULL_BEHAVIOR
        }
      ]
    }
  ])

  tags = merge(var.base_tags, {
    Name                          = "${var.resource_prefix}-eugene-search-ws-task"
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

resource "aws_ecs_service" "search_web_service" {
  name            = "${var.resource_prefix}-eugene-search-ws"
  cluster         = var.ecs_uspto_cluster_name
  task_definition = aws_ecs_task_definition.web_service_search_task.arn
  desired_count   = 2
  launch_type     = "FARGATE"
  deployment_minimum_healthy_percent = 50
  force_new_deployment = true

  for_each = toset([for s in data.aws_subnet.uspto_subnets : s.id])
  network_configuration {
    security_groups  = [aws_security_group.eugene_search_container_sg.id]
    subnets          = toset([one([each.value])])
    assign_public_ip = false
  }

  wait_for_steady_state = true

  load_balancer {
    target_group_arn = "${aws_lb_target_group.eugene_search_alb_ip_target_group.arn}"
    container_name   = "search_ws"
    container_port   = 8000
  }

  tags = merge(var.base_tags, {
    Name =  "${var.resource_prefix}-eugene-search-ws"
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
