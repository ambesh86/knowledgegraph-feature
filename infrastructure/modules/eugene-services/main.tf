module "uspto" {
  source = "./uspto"

  aws_region = var.aws_region
  ecs_uspto_cluster_name = var.ecs_uspto_cluster_name
  subnets = var.subnets
  vpc_id = var.vpc_id

  resource_prefix = var.resource_prefix
  workload_name = var.workload_name

  ecs_execution_role_arn=var.ecs_execution_role_arn
  ecs_task_role_arn=var.ecs_task_role_arn

  search_ws_image_hash = var.search_ws_image_hash
  search_trainer_image_hash = var.search_trainer_image_hash
}
