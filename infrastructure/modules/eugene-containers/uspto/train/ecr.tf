resource "aws_ecr_repository" "eugene_search_trainer_repo" {
  name                 = "eugene/patent_search_trainer"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(var.base_tags, {
    workloadName = var.workload_name
  })

}