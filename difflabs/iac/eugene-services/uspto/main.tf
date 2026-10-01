module "train" {
  source = "./train"

  aws_region = var.aws_region
  ecs_uspto_cluster_name = aws_ecs_cluster.uspto_cluster.name
  ecs_uspto_cluster_arn = aws_ecs_cluster.uspto_cluster.arn
  uspto_ecs_task_execution_role_arn = aws_iam_role.uspto_ecs_task_execution_role.arn
  uspto_ecs_task_role_arn = aws_iam_role.uspto_ecs_task_role.arn
  subnets = var.subnets
  vpc_id = var.vpc_id
  base_tags = local.base_tags
  dotenv = local.dotenv
  uspto_env = local.uspto_env
  account_type                     = var.account_type
  ams_managed                      = var.ams_managed
  ams_monitoring_policy            = var.ams_monitoring_policy
  ams_monitoring_policy_platform   = var.ams_monitoring_policy_platform
  apm                              = var.apm
  business_unit                    = var.business_unit
  cost_budget_amount               = var.cost_budget_amount
  cost_center                      = var.cost_center
  data_classification              = var.data_classification
  patch_schedule                   = var.patch_schedule
  resource_prefix                  = var.resource_prefix
  technical_owner                  = var.technical_owner
  workload_environment             = var.workload_environment
  workload_name                    = var.workload_name
  workload_owner                   = var.workload_owner

  depends_on = [aws_iam_role.uspto_ecs_task_role, aws_iam_role.uspto_ecs_task_execution_role, aws_ecs_cluster.uspto_cluster]
}

module "search" {
  source = "./search"

  aws_region = var.aws_region
  ecs_uspto_cluster_name = aws_ecs_cluster.uspto_cluster.name
  uspto_ecs_task_execution_role_arn = aws_iam_role.uspto_ecs_task_execution_role.arn
  uspto_ecs_task_role_arn = aws_iam_role.uspto_ecs_task_role.arn
  subnets = var.subnets
  vpc_id = var.vpc_id
  base_tags = local.base_tags
  dotenv = local.dotenv
  uspto_env = local.uspto_env
  account_type                     = var.account_type
  ams_managed                      = var.ams_managed
  ams_monitoring_policy            = var.ams_monitoring_policy
  ams_monitoring_policy_platform   = var.ams_monitoring_policy_platform
  apm                              = var.apm
  business_unit                    = var.business_unit
  cost_budget_amount               = var.cost_budget_amount
  cost_center                      = var.cost_center
  data_classification              = var.data_classification
  patch_schedule                   = var.patch_schedule
  resource_prefix                  = var.resource_prefix
  technical_owner                  = var.technical_owner
  workload_environment             = var.workload_environment
  workload_name                    = var.workload_name
  workload_owner                   = var.workload_owner

  depends_on = [aws_iam_role.uspto_ecs_task_role, aws_iam_role.uspto_ecs_task_execution_role, aws_ecs_cluster.uspto_cluster]
}

module "mcp" {
  source = "./mcp"

  aws_region = var.aws_region
  ecs_uspto_cluster_name = aws_ecs_cluster.uspto_cluster.name
  uspto_ecs_task_execution_role_arn = aws_iam_role.uspto_ecs_task_execution_role.arn
  uspto_ecs_task_role_arn = aws_iam_role.uspto_ecs_task_role.arn
  subnets = var.subnets
  vpc_id = var.vpc_id
  base_tags = local.base_tags
  dotenv = local.dotenv
  uspto_env = local.uspto_env
  account_type                     = var.account_type
  ams_managed                      = var.ams_managed
  ams_monitoring_policy            = var.ams_monitoring_policy
  ams_monitoring_policy_platform   = var.ams_monitoring_policy_platform
  apm                              = var.apm
  business_unit                    = var.business_unit
  cost_budget_amount               = var.cost_budget_amount
  cost_center                      = var.cost_center
  data_classification              = var.data_classification
  patch_schedule                   = var.patch_schedule
  resource_prefix                  = var.resource_prefix
  technical_owner                  = var.technical_owner
  workload_environment             = var.workload_environment
  workload_name                    = var.workload_name
  workload_owner                   = var.workload_owner

  depends_on = [aws_iam_role.uspto_ecs_task_role, aws_iam_role.uspto_ecs_task_execution_role, aws_ecs_cluster.uspto_cluster]
}

module "agent" {
  source = "./agent"

  aws_region = var.aws_region
  ecs_uspto_cluster_name = aws_ecs_cluster.uspto_cluster.name
  uspto_ecs_task_execution_role_arn = aws_iam_role.uspto_ecs_task_execution_role.arn
  uspto_ecs_task_role_arn = aws_iam_role.uspto_ecs_task_role.arn
  subnets = var.subnets
  vpc_id = var.vpc_id
  base_tags = local.base_tags
  dotenv = local.dotenv
  uspto_env = local.uspto_env
  account_type                     = var.account_type
  ams_managed                      = var.ams_managed
  ams_monitoring_policy            = var.ams_monitoring_policy
  ams_monitoring_policy_platform   = var.ams_monitoring_policy_platform
  apm                              = var.apm
  business_unit                    = var.business_unit
  cost_budget_amount               = var.cost_budget_amount
  cost_center                      = var.cost_center
  data_classification              = var.data_classification
  patch_schedule                   = var.patch_schedule
  resource_prefix                  = var.resource_prefix
  technical_owner                  = var.technical_owner
  workload_environment             = var.workload_environment
  workload_name                    = var.workload_name
  workload_owner                   = var.workload_owner

  depends_on = [aws_iam_role.uspto_ecs_task_role, aws_iam_role.uspto_ecs_task_execution_role, aws_ecs_cluster.uspto_cluster]
}

module "agent-ui" {
  source = "./agent-ui"

  aws_region = var.aws_region
  ecs_uspto_cluster_name = aws_ecs_cluster.uspto_cluster.name
  uspto_ecs_task_execution_role_arn = aws_iam_role.uspto_ecs_task_execution_role.arn
  uspto_ecs_task_role_arn = aws_iam_role.uspto_ecs_task_role.arn
  subnets = var.subnets
  vpc_id = var.vpc_id
  base_tags = local.base_tags
  dotenv = local.dotenv
  uspto_env = local.uspto_env
  account_type                     = var.account_type
  ams_managed                      = var.ams_managed
  ams_monitoring_policy            = var.ams_monitoring_policy
  ams_monitoring_policy_platform   = var.ams_monitoring_policy_platform
  apm                              = var.apm
  business_unit                    = var.business_unit
  cost_budget_amount               = var.cost_budget_amount
  cost_center                      = var.cost_center
  data_classification              = var.data_classification
  patch_schedule                   = var.patch_schedule
  resource_prefix                  = var.resource_prefix
  technical_owner                  = var.technical_owner
  workload_environment             = var.workload_environment
  workload_name                    = var.workload_name
  workload_owner                   = var.workload_owner

  depends_on = [aws_iam_role.uspto_ecs_task_role, aws_iam_role.uspto_ecs_task_execution_role, aws_ecs_cluster.uspto_cluster]
}

module "canaries" {
  source = "./canaries"

  aws_region = var.aws_region
  ecs_uspto_cluster_name = aws_ecs_cluster.uspto_cluster.name
  ecs_uspto_cluster_arn = aws_ecs_cluster.uspto_cluster.arn
  uspto_ecs_task_execution_role_arn = aws_iam_role.uspto_ecs_task_execution_role.arn
  uspto_ecs_task_role_arn = aws_iam_role.uspto_ecs_task_role.arn
  uspto_event_bridge_role_arn = aws_iam_role.cloudwatch_events_ecs_role.arn
  subnets = var.subnets
  vpc_id = var.vpc_id
  base_tags = local.base_tags
  dotenv = local.dotenv
  uspto_env = local.uspto_env
  account_type                     = var.account_type
  ams_managed                      = var.ams_managed
  ams_monitoring_policy            = var.ams_monitoring_policy
  ams_monitoring_policy_platform   = var.ams_monitoring_policy_platform
  apm                              = var.apm
  business_unit                    = var.business_unit
  cost_budget_amount               = var.cost_budget_amount
  cost_center                      = var.cost_center
  data_classification              = var.data_classification
  patch_schedule                   = var.patch_schedule
  resource_prefix                  = var.resource_prefix
  technical_owner                  = var.technical_owner
  workload_environment             = var.workload_environment
  workload_name                    = var.workload_name
  workload_owner                   = var.workload_owner

  depends_on = [aws_iam_role.cloudwatch_events_ecs_role, aws_iam_role.uspto_ecs_task_role, aws_iam_role.uspto_ecs_task_execution_role, aws_ecs_cluster.uspto_cluster]
}
