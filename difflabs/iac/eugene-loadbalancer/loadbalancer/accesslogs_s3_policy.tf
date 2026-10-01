data "aws_elb_service_account" "lb_account" {}


resource "aws_s3_bucket_policy" "s3_lb_write_policy" {
  bucket = "${aws_s3_bucket.eugene_logs_s3.id}"

  policy = <<POLICY
{
  "Id": "s3_lb_write_policy",
  "Version": "2012-10-17",
  "Statement": [
    {
        "Sid": "s3_lb_write_statement",
        "Action": [
            "s3:PutObject"
        ],
        "Effect": "Allow",
        "Resource": "arn:aws:s3:::${var.logs_bucket}/*",
        "Principal": {
            "AWS": [
                "${data.aws_elb_service_account.lb_account.arn}"
            ]
        }
    }
  ]
}
POLICY

}