data "aws_vpc" "eugene_vpc" {
  id = var.vpc_id
}

data "aws_subnet" "eugene_subnets" {
  for_each = toset(var.subnets)
  id       = each.value
}