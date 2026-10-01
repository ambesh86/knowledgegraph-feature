# Create ECS task definition for web service
# WARN: if this is a private vpc you may need to setup endpoints
# TODO: setup endpoint automatically
# https://repost.aws/knowledge-center/ecs-fargate-pull-container-error
resource "aws_ecs_task_definition" "eugene_bastion_task" {
  family                = "${var.resource_prefix}-eugene-bastion-task"
  network_mode           = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn      = aws_iam_role.bastion_ecs_execution_role.arn
  task_role_arn           = aws_iam_role.bastion_ecs_task_role.arn
  cpu       = 1024
  memory    = 2048

  container_definitions = jsonencode([
    {
      name      = "eguene-bastion"
      image     = local.bastion_image
      essential = true

      logConfiguration = {
        logDriver = "awslogs"
        options   = {
            "awslogs-group"         = aws_cloudwatch_log_group.eugene_bastion_service_log_group.name
            "awslogs-region"        = var.aws_region
            "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command = ["CMD-SHELL", "uptime || exit 1"]
        interval = 90
        timeout = 5
        retries = 3
      }

      environment = [
        # may need to force new deployment e.g.
        # aws ecs update-service --cluster stage-eugene-uspto-cluster --service stage-eugene-search-ws --force-new-deployment
      ]
    }
  ])

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-bastion-task"
    workloadName = var.workload_name
  })
}

resource "aws_ecs_service" "eugene_bastion_service" {
  name            = "${var.resource_prefix}-eugene-bastion"
  cluster         = var.ecs_database_cluster_name
  task_definition = aws_ecs_task_definition.eugene_bastion_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  enable_execute_command = true

  for_each = toset([for s in data.aws_subnet.database_subnets : s.id])
  network_configuration {
    security_groups  = [aws_security_group.eugene_bastion_container_sg.id]
    subnets          = toset([one([each.value])])
    assign_public_ip = false
  }

  tags = merge(var.base_tags, {
    Name =  "${var.resource_prefix}-eugene-bastion"
    workloadName = var.workload_name
  })
}

