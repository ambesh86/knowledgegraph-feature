# deprecated
# the database is running on ec2 and not ecs
# todo: delete this module
module "database" {
  source = "./database"

  aws_region = var.aws_region
  ecs_database_cluster_name = var.ecs_database_cluster_name
  subnets = var.subnets
  vpc_id = var.vpc_id

  resource_prefix = var.resource_prefix
  workload_name = var.workload_name

  ecs_execution_role_arn=var.ecs_execution_role_arn
  ecs_task_role_arn=var.ecs_task_role_arn
  ecs_service_role_arn=var.ecs_service_role_arn

  database_image_hash = var.database_image_hash
}
