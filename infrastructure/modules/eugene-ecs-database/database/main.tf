module "neo4j-ce" {
  source = "./neo4j-ce"

  aws_region = var.aws_region

  ecs_cluster_name = aws_ecs_cluster.database_cluster.name
  subnets = var.subnets
  vpc_id = var.vpc_id
  base_tags = local.base_tags

  resource_prefix = var.resource_prefix
  workload_name = var.workload_name

  ecs_execution_role_arn=var.ecs_execution_role_arn
  ecs_task_role_arn=var.ecs_task_role_arn
  ecs_service_role_arn=var.ecs_service_role_arn

  image_hash = var.database_image_hash

  depends_on = [
    aws_ecs_cluster.database_cluster
  ]
}
