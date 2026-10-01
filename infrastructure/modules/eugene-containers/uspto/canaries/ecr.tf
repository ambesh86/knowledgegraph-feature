
resource "aws_ecr_repository" "eugene_api_canaries_repo" {
  name                 = "eugene/api_canaries"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(var.base_tags, {
    workloadName = var.workload_name
  })
}