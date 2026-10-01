# Create a security group for the EC2 instance
resource "aws_security_group" "eugene_database_instance_sg" {
  name        = "${var.resource_prefix}-eugene-database-instance-sg"
  description = "Allow NEO4J and SSH traffic"
  vpc_id      = var.vpc_id

  tags = merge(local.base_tags, {
    Name = "${var.resource_prefix}-eugene-database-instance-sg",
    workloadName = var.workload_name
  })
}


resource "aws_vpc_security_group_ingress_rule" "eugene_database_instance_allow_http_rule" {
  security_group_id = aws_security_group.eugene_database_instance_sg.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 7687
  to_port           = 7687
  ip_protocol       = "tcp"
  description       = "neo4j database"
}

resource "aws_vpc_security_group_egress_rule" "eugene_database_instance_allow_egress_rule" {
  security_group_id = aws_security_group.eugene_database_instance_sg.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1" 
}

