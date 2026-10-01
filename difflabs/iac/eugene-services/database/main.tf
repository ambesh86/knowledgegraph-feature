module "neo4j-ce" {
  source = "./neo4j-ce"

  aws_region = var.aws_region

  ecs_database_cluster_name = aws_ecs_cluster.database_cluster.name
  subnets = var.subnets
  vpc_id = var.vpc_id
  base_tags = local.base_tags

  dotenv = local.dotenv
  resource_prefix = var.resource_prefix
  workload_name = var.workload_name

  depends_on = [
    aws_ecs_cluster.database_cluster
  ]
}
