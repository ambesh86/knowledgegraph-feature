terraform {
  backend "s3" {
    # bucket = "kg-experiments-terraform-state"
    # key    = "eugene-containers/us-east-1/stage"
    bucket = "eugene-iac-difflabs"
    key    = "eugene-containers/us-east-1/stage"
    region = "us-east-1"
  }
}