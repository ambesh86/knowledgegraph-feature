data "aws_subnets" "database_subnets" {
  filter {
    name   = "tag:Name"
    values = var.subnets
  }
}