resource "aws_iam_role" "uspto_ecs_task_execution_role" {
  name = "${var.resource_prefix}-uspto_ecs_task_execution_role"

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

  tags = merge(local.base_tags, {
    Name = "${var.resource_prefix}-uspto-ecs-execution-role"
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

resource "aws_iam_role_policy" "uspto_ecs_pull_role_policy" {
    role     = aws_iam_role.uspto_ecs_task_execution_role.id
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
          Resource = "arn:aws:ecs:${var.aws_region}:*:task/*-uspto-cluster/*"
          
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
          Resource = "arn:aws:ecs:${var.aws_region}:*:task/*-uspto-cluster/*"
      }
    ]
  })

}

resource "aws_iam_role_policy_attachment" "uspto_ecs_attach_execution_role" {
    role       = aws_iam_role.uspto_ecs_task_execution_role.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
