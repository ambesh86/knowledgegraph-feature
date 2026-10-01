resource "aws_security_group" "eugene_bastion_container_sg" {
  name        = "${var.resource_prefix}-eugene-bastion-container-sg"
  description = "Allow inbound traffic and all outbound traffic to the search container"
  vpc_id      = data.aws_vpc.database_vpc.id

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-bastion-container-sg"
    workloadName = var.workload_name
  })
}

resource "aws_vpc_security_group_ingress_rule" "eugene_bastion_container_allow_http_rule" {
  security_group_id = aws_security_group.eugene_bastion_container_sg.id
  cidr_ipv4         = data.aws_vpc.database_vpc.cidr_block
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "eugene_bastion_container_allow_egress_rule" {
  security_group_id = aws_security_group.eugene_bastion_container_sg.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1" 
}
