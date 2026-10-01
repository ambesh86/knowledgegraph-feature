terraform {
  backend "s3" {
    bucket = "eugene-iac-difflabs"
    key    = "eugene-database/eu-central-1/stage"
    region = "us-east-1"
  }
}