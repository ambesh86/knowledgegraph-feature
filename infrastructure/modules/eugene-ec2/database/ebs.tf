resource "aws_ebs_volume" "eugene_data_volume" {
  availability_zone = var.aws_availability_zone
  size              = 128
  type              = "gp3"
  encrypted         = true

  tags = merge(local.base_tags, {
    Name = "${var.resource_prefix}-eugene-database-instance-volume",
    workloadName = var.workload_name
  })
}
