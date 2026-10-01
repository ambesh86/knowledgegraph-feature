# =============================================================================
# IAM for the workloads on this box.
#
# Split from ec2.tf because these grants belong to what the instance *does*
# (read images, read and write scan/extraction artifacts), not to how it is
# built. Each is scoped to the buckets actually in use rather than "*".
# =============================================================================

# ECR pull. Required whenever ui_image/scout_image/ade_image point at ECR —
# which is the recommended setup, because ECR resolves over the VPC endpoints
# and needs no internet, unlike ghcr.io.
resource "aws_iam_role_policy_attachment" "ecr_read" {
  count      = local.use_ecr ? 1 : 0
  role       = aws_iam_role.ui.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

locals {
  service_buckets = compact([
    var.enable_scout ? var.scout_s3_bucket : "",
    var.enable_ade ? var.ade_s3_bucket : "",
  ])
}

resource "aws_iam_role_policy" "service_s3" {
  count = length(local.service_buckets) > 0 ? 1 : 0
  name  = "${var.name_prefix}-service-s3"
  role  = aws_iam_role.ui.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = ["s3:ListBucket"],
        Resource = [for b in local.service_buckets : "arn:aws:s3:::${b}"]
      },
      {
        Effect   = "Allow",
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
        Resource = [for b in local.service_buckets : "arn:aws:s3:::${b}/*"]
      }
    ]
  })
}
