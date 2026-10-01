# todo: delete this code after resources are destroyed

# module "eugene_ecs_database" {
#   source = "../../modules/eugene-ecs-database"

#   aws_region=var.aws_region
#   workload_name=var.workload_name
#   resource_prefix=var.resource_prefix
#   subnets=var.subnets
#   vpc_id=var.vpc_id
#   ecs_database_cluster_name=var.ecs_database_cluster_name

#   ecs_execution_role_arn=var.ecs_execution_role_arn
#   ecs_task_role_arn=var.ecs_task_role_arn
#   ecs_service_role_arn=var.ecs_service_role_arn

#   database_image_hash=var.database_image_hash
# }
