resource "aws_iam_role" "bastion_ecs_task_role" {
  name = "${var.resource_prefix}-eugene-bastion-ecs-task-role"

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
    Name = "${var.resource_prefix}-eugene-bastion-ecs-task-role"
    workloadName = var.workload_name
  })
}

resource "aws_iam_role_policy_attachment" "bastion_ecs_attach_task_role0" {
    role       = aws_iam_role.bastion_ecs_task_role.name
    policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "bastion_ecs_attach_task_role1" {
    role       = aws_iam_role.bastion_ecs_task_role.name
    policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}
