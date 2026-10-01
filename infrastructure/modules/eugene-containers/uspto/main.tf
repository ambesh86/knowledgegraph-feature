module "ingest" {
  source = "./ingest"

  base_tags = local.base_tags
  resource_prefix = var.resource_prefix
  workload_name = var.workload_name
}

module "train" {
  source = "./train"

  base_tags = local.base_tags
  resource_prefix = var.resource_prefix
  workload_name = var.workload_name
}

module "search" {
  source = "./search"

  base_tags = local.base_tags
  resource_prefix = var.resource_prefix
  workload_name = var.workload_name
}
