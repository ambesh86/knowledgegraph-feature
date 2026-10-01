resource "aws_ecr_repository" "eugene_neo4j_ce_repo" {
  name                 = "eugene/neo4j_ce"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(var.base_tags, {
    workloadName = var.workload_name
  })
}