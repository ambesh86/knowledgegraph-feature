module "neo4j-ce" {
  source = "./neo4j-ce"

  base_tags = local.base_tags
  resource_prefix = var.resource_prefix
  workload_name = var.workload_name
}
