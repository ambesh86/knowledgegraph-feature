resource "aws_security_group" "eugene_train_allow_sg" {
  name        = "${var.resource_prefix}-eugene-train-allow-sg"
  description = "Allow all outbound traffic"
  vpc_id      = data.aws_vpc.uspto_vpc.id

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-train-allow-sg"
    workloadName = var.workload_name
  })
}

resource "aws_vpc_security_group_egress_rule" "eugene_train_allow_egress_rule" {
  security_group_id = aws_security_group.eugene_train_allow_sg.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}