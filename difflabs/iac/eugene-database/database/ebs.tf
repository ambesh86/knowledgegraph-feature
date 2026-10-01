resource "aws_ebs_volume" "eugene_data_volume" {
  availability_zone = "eu-central-1b"
  size              = 64
  type              = "gp3"

  tags = merge(local.base_tags, {
    Name = "${var.resource_prefix}-euGENE-1",
    workloadName = var.workload_name
  })
}
