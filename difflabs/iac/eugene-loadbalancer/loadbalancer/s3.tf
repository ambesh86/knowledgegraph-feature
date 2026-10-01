resource "aws_s3_bucket" "eugene_logs_s3" {
  bucket = "${var.logs_bucket}"
  tags = merge(local.base_tags, {
    Name = "${var.logs_bucket}"
    workloadName = var.workload_name
  })
}


resource "aws_s3_bucket_ownership_controls" "eugene_logs_s3_controls" {
  bucket = aws_s3_bucket.eugene_logs_s3.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "eugene_logs_s3_acl" {
  depends_on = [aws_s3_bucket_ownership_controls.eugene_logs_s3_controls]

  bucket = aws_s3_bucket.eugene_logs_s3.id
  acl    = "private"
}


resource "aws_s3_bucket_server_side_encryption_configuration" "eugene_logs_s3_sse" {
  bucket = aws_s3_bucket.eugene_logs_s3.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "AES256"
    }
  }
}