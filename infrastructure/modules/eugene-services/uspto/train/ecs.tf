# Create ECS task definition for training
resource "aws_ecs_task_definition" "training_task" {
  family                 = "${var.resource_prefix}-training-task"
  cpu                    = 1024
  memory                 = 2048
  network_mode           = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn      = var.ecs_execution_role_arn
  task_role_arn           = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name      = "patent_search_trainer"
      image     = "${local.search_trainer_image}"
      cpu       = 1024
      memory    = 2048
      essential = true

      logConfiguration = {
        logDriver = "awslogs"
        options   = {
            "awslogs-group"         = aws_cloudwatch_log_group.training_service_log_group.name
            "awslogs-region"        = var.aws_region
            "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command = ["CMD-SHELL", "date || exit 1"]
        interval = 90
        timeout = 5
        retries = 3
      }

      environment = [
        {
          name  = "HF_HUB_OFFLINE"
          value = var.dotenv.HF_HUB_OFFLINE
        }
      ]
    }
  ])


  tags = merge(var.base_tags,  {
    Name = "${var.resource_prefix}-training-task"
    workloadName = var.workload_name
  })
}

resource "aws_ecs_service" "training_service" {
  name            = "${var.resource_prefix}-eugene-training-service"
  cluster         = var.ecs_uspto_cluster_name
  task_definition = aws_ecs_task_definition.training_task.arn
  desired_count   = 0
  launch_type     = "FARGATE"

  for_each = toset([for s in data.aws_subnet.uspto_subnets : s.id])
  network_configuration {
    security_groups  = [aws_security_group.eugene_train_allow_sg.id]
    subnets          = toset([one([each.value])])
    assign_public_ip = false
  }

  wait_for_steady_state = true 

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-training-service"
    workloadName = var.workload_name
  })
}
