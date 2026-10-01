terraform {
  backend "s3" {
    bucket = "eugene-iac-difflabs"
    key    = "eugene-loadbalancer/us-east-1/stage"
    region = "us-east-1"
  }
}