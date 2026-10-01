resource "aws_ecr_repository" "eugene_patent_ingest_repo" {
  name                 = "eugene/patent_ingest"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(var.base_tags, {
    workloadName = var.workload_name
  })
}