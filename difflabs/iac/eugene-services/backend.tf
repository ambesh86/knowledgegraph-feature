terraform {
  backend "s3" {
    bucket = "eugene-iac-difflabs"
    key    = "eugene-services/us-east-1/stage"
    region = "us-east-1"
  }
}