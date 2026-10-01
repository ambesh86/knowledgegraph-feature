resource "aws_iam_role" "uspto_ecs_task_role" {
  name = "${var.resource_prefix}-uspto_ecs_task_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(local.base_tags, {
    Name = "${var.resource_prefix}-uspto-ecs-task=role"
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

resource "aws_iam_role_policy" "uspto_ecs_task_role_policy" {
    role     = aws_iam_role.uspto_ecs_task_role.id
    policy   = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
          Effect = "Allow"
          Action = [
              "cloudwatch:PutMetricData"
          ]
          Resource = "*"
          Condition = {
            StringEquals = {
              "cloudwatch:namespace" = "CSL/euGENE"
            }
          }
      },
      {
          Effect = "Allow"
          Action = [
              "secretsmanager:GetSecretValue",
              "secretsmanager:ListSecrets",
              "secretsmanager:DescribeSecret"
          ]
          Resource = "arn:aws:secretsmanager:${var.aws_region}:*:secret:eugene/*/*/env*"
      }
    ]
  })
}
