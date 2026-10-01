module "uspto" {
  source = "./uspto"

  resource_prefix = var.resource_prefix
  workload_name = var.workload_name
}

module "database" {
  source = "./database"

  resource_prefix = var.resource_prefix
  workload_name = var.workload_name
}

