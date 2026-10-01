# Create instance profile
resource "aws_iam_instance_profile" "eugene_database_instance_profile" {
  name = "${var.resource_prefix}-eugene-database-instance-profile"
  role = "${var.ec2_instance_role_name}"

  tags = merge(local.base_tags, {
    Name = "${var.resource_prefix}-eugene-database-instance-profile",
    workloadName = var.workload_name
  })
}
