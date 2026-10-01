module "eugene_containers" {
  source = "../../modules/eugene-containers"

  aws_region=var.aws_region
  workload_name=var.workload_name
  resource_prefix=var.resource_prefix
}

module "eugene_services" {
  source = "../../modules/eugene-services"

  aws_region=var.aws_region
  workload_name=var.workload_name
  resource_prefix=var.resource_prefix
  subnets=var.subnets
  vpc_id=var.vpc_id
  ecs_uspto_cluster_name=var.ecs_uspto_cluster_name

  ecs_execution_role_arn=var.ecs_execution_role_arn
  ecs_task_role_arn=var.ecs_task_role_arn
  ecs_service_role_arn=var.ecs_service_role_arn
}
