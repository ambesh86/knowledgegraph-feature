data "aws_vpc" "uspto_vpc" {
  id = var.vpc_id
}

data "aws_subnet" "uspto_subnets" {
  for_each = toset(var.subnets)
  id       = each.value
}