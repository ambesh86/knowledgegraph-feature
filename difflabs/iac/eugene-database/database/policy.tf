resource "aws_iam_role" "eugene_db_role" {
  name = "${var.resource_prefix}-eugene-db-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(local.base_tags, {
    Name = "${var.resource_prefix}-eugene-db-role",
    workloadName = var.workload_name
  })
}

# Attach SSM policy to the role
resource "aws_iam_role_policy_attachment" "ssm_policy" {
  role       = aws_iam_role.eugene_db_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}


# Create instance profile
resource "aws_iam_instance_profile" "ssm_profile" {
  name = "${var.resource_prefix}-ssm-profile"
  role = aws_iam_role.eugene_db_role.name

  tags = merge(local.base_tags, {
    Name = "${var.resource_prefix}-eugene-database-instance-profile",
    workloadName = var.workload_name
  })
}
