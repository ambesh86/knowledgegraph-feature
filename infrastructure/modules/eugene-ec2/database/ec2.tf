data "template_file" "startup" {
 template = file("${path.module}/templates/ssm-agent-installer.sh")
}

# Create an EC2 instance
resource "aws_instance" "eugene_database_instance" {
  ami           = data.aws_ami.amazon_linux_2.id
  instance_type = var.instance_type

  iam_instance_profile = aws_iam_instance_profile.eugene_database_instance_profile.name

  vpc_security_group_ids = [
    aws_security_group.eugene_database_instance_sg.id
  ]
  subnet_id = var.subnet

  tags = merge(local.base_tags, {
    Name = "${var.resource_prefix}-euGENE-1",
    workloadName = var.workload_name
  })

  monitoring = true
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  user_data = data.template_file.startup.rendered
}


