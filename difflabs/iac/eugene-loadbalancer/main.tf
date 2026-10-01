module "loadbalancer" {
  source = "./loadbalancer"

  subnets = var.subnets
  vpc_id = var.vpc_id

  resource_prefix = var.resource_prefix
  workload_name = var.workload_name
  logs_bucket = var.logs_bucket
}
