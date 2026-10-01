
resource "aws_ecr_repository" "eugene_search_ws_repo" {
  name                 = "eugene/search_ws"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(var.base_tags, {
    workloadName = var.workload_name
  })
}