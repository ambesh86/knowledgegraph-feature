resource "aws_iam_role" "bastion_ecs_service_role" {
  name = "${var.resource_prefix}-eugene-bastion-ecs-service-role"

  # https://docs.aws.amazon.com/AmazonECS/latest/developerguide/infrastructure_IAM_role.html
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AssumeRoleToECSForInfrastructureManagement"
        Effect = "Allow"
        Principal = {
          Service = "ecs.amazonaws.com" 
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-bastion-ecs-service-role"
    workloadName = var.workload_name
  })
}

resource "aws_iam_role_policy" "bastion_ecs_service_pass_role_policy" {
    role     = aws_iam_role.bastion_ecs_service_role.id
    policy   = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "PassRoleToECSForInfrastructureManagement"
        Effect = "Allow"
        Resource = ["arn:aws:iam::*:role/${aws_iam_role.bastion_ecs_service_role.name}"]
        Action = "iam:PassRole"
        Condition = {
          StringEquals = {
            "iam:PassedToService": "ecs.amazonaws.com"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "bastion_ecs_service_attach_role0" {
    role       = aws_iam_role.bastion_ecs_service_role.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRolePolicyForVolumes"
}
