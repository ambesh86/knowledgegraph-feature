resource "aws_iam_role" "bastion_ecs_execution_role" {
  name = "${var.resource_prefix}-eugene-bastion-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
  
  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-bastion-ecs-execution-role"
    workloadName = var.workload_name
  })
}

resource "aws_iam_role_policy" "bastion_ecs_pull_execution_role_policy" {
    role     = aws_iam_role.bastion_ecs_execution_role.id
    policy   = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { 
          Effect = "Allow"
          Action = [
              "ecr:GetAuthorizationToken",
              "logs:CreateLogStream",
              "logs:PutLogEvents"
          ]
          Resource = "arn:aws:ecs:*:*:task/${var.ecs_database_cluster_name}/*"
      },
      {
          Effect = "Allow"
          Action: [
              "ecr:BatchCheckLayerAvailability",
              "ecr:GetDownloadUrlForLayer",
              "ecr:BatchGetImage"
          ]
          Condition = {
              StringEquals = {
                  "aws:sourceVpc": "${var.vpc_id}"
              }
          }
          Resource = "arn:aws:ecs:*:*:task/${var.ecs_database_cluster_name}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "bastion_ecs_attach_execution_role0" {
    role       = aws_iam_role.bastion_ecs_execution_role.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}