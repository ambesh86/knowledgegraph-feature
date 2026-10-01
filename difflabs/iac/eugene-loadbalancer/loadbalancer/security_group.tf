resource "aws_security_group" "eugene_search_lb_sg" {
  name        = "eugene_search_lb_sg"
  description = "Allow eugene search loadbalancer ingress/egress traffic"
  vpc_id      = var.vpc_id

  tags = merge(var.base_tags, {
    Name = "eugene_search_lb_sg",
    workloadName = var.workload_name
  })
}

resource "aws_vpc_security_group_ingress_rule" "allow_http" {
  security_group_id = aws_security_group.eugene_search_lb_sg.id
  description       = "allow http"
  cidr_ipv4         = data.aws_vpc.eugene_vpc.cidr_block
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_ingress_rule" "allow_https" {
  security_group_id = aws_security_group.eugene_search_lb_sg.id
  description       = "allow https"
  cidr_ipv4         = data.aws_vpc.eugene_vpc.cidr_block
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_ingress_rule" "allow_vpn" {
  security_group_id = aws_security_group.eugene_search_lb_sg.id
  description       = "allow vpn connectivity"
  cidr_ipv4         = "10.0.0.0/8"
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_egress_rule" "eugene_lb_allow_all_egress" {
  security_group_id = aws_security_group.eugene_search_lb_sg.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}
