data "aws_subnets" "uspto_subnets" {
  filter {
    name   = "tag:Name"
    values = var.subnets
  }
}