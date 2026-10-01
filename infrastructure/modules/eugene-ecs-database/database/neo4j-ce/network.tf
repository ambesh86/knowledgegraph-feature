data "aws_vpc" "database_vpc" {
  id = var.vpc_id
}

data "aws_subnet" "database_subnets" {
  for_each = toset(var.subnets)
  id       = each.value
}