# Create ECS task definition for web service
# WARN: if this is a private vpc you may need to setup endpoints
# TODO: setup endpoint automatically
# https://repost.aws/knowledge-center/ecs-fargate-pull-container-error
resource "aws_ecs_task_definition" "eugene_database_task" {
  family                = "${var.resource_prefix}-eugene-database-task"
  network_mode           = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn      = var.ecs_execution_role_arn
  task_role_arn           = var.ecs_task_role_arn
  cpu       = 4096
  memory    = 16384

  container_definitions = jsonencode([
    {
      name      = "eguene-neo4j-ce"
      image     = "${local.database_image}"
      essential = true
      portMappings = [
        {
          containerPort = 7687
          hostPort      = 7687
          protocol      = "tcp"
        }
      ]

      mountPoints = [
        {
            sourceVolume = "eugene-data-volume"
            containerPath = "/data"
            readOnly = false
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options   = {
            "awslogs-group"         = aws_cloudwatch_log_group.eugene_database_service_log_group.name
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

  volume {
    name = "eugene-data-volume"
    configure_at_launch = true
  }

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-database-task"
    workloadName = var.workload_name
  })
}

resource "aws_ecs_service" "eugene_database_service" {
  name            = "${var.resource_prefix}-eugene-database"
  cluster         = var.ecs_cluster_name
  task_definition = aws_ecs_task_definition.eugene_database_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  enable_execute_command = true

  for_each = toset([for s in data.aws_subnet.database_subnets : s.id])
  network_configuration {
    security_groups  = [aws_security_group.eugene_database_container_sg.id]
    subnets          = toset([one([each.value])])
    assign_public_ip = false
  }

  volume_configuration {
    name = "eugene-data-volume"
    managed_ebs_volume {
      role_arn = var.ecs_service_role_arn
      encrypted = true
      iops = 3000
      size_in_gb = 128 
      volume_type = "gp3"
      throughput = 125
      tag_specifications {
        resource_type = "volume"
        tags = merge(var.base_tags, {
          Name = "${var.resource_prefix}-eugene-database-volume"
          workloadName = var.workload_name
        })
        propagate_tags = "NONE"
      }
    }
  }

  tags = merge(var.base_tags, {
    Name =  "${var.resource_prefix}-eugene-database"
    workloadName = var.workload_name
  })
}

