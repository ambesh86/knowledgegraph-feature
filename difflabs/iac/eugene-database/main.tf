module "database" {
  source = "./database"

  subnet = var.subnet
  vpc_id = var.vpc_id

  resource_prefix = var.resource_prefix
  workload_name = var.workload_name
}
