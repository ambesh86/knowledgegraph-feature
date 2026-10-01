module "train" {
  source = "./train"

  aws_region = var.aws_region
  ecs_uspto_cluster_name = aws_ecs_cluster.uspto_cluster.name
  ecs_uspto_cluster_arn = aws_ecs_cluster.uspto_cluster.arn
  subnets = var.subnets
  vpc_id = var.vpc_id
  base_tags = local.base_tags
  dotenv = local.dotenv
  resource_prefix = var.resource_prefix
  workload_name = var.workload_name

  ecs_execution_role_arn=var.ecs_execution_role_arn
  ecs_task_role_arn=var.ecs_task_role_arn

  image_hash = var.search_trainer_image_hash

  depends_on = [aws_ecs_cluster.uspto_cluster]
}

module "search" {
  source = "./search"

  aws_region = var.aws_region
  ecs_uspto_cluster_name = aws_ecs_cluster.uspto_cluster.name
  subnets = var.subnets
  vpc_id = var.vpc_id
  base_tags = local.base_tags
  dotenv = local.dotenv
  resource_prefix = var.resource_prefix
  workload_name = var.workload_name

  ecs_execution_role_arn=var.ecs_execution_role_arn
  ecs_task_role_arn=var.ecs_task_role_arn

  image_hash = var.search_ws_image_hash

  depends_on = [aws_ecs_cluster.uspto_cluster]
}
