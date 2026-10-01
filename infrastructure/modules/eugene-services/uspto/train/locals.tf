locals {
    search_trainer_image = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/eugene/patent_search_trainer:${var.image_hash}"
}