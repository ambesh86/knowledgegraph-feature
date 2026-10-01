resource "aws_lb_target_group" "eugene_search_alb_ip_target_group" {
  name        = "eugene-search-lb-tg"
  port        = 80
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id
  tags = merge(local.base_tags, {
    Name = "eugene-search-lb-tg"
  })
}

resource "aws_lb" "eugene_search_alb" {
  name               = "eugene-search-alb"
  internal           = true
  load_balancer_type = "application"
  security_groups    = [aws_security_group.eugene_search_lb_sg.id]

  subnets = var.subnets

  # todo: set delete protect to true on prod
  enable_deletion_protection = false

  drop_invalid_header_fields = true

  access_logs {
    bucket  = "${aws_s3_bucket.eugene_logs_s3.bucket}"
    prefix  = "eugene-search-alb"
    enabled = true
  }

  tags = merge(local.base_tags, {
    Name = "eugene-search-alb",
    workloadName = var.workload_name
  })
}

# this will be created by the cloud team and cannot be automated by our scripts
# resource "aws_lb_listener" "eugene_search_alb_listener" {
#   load_balancer_arn = aws_lb.eugene_search_alb.arn
#   port              = "80"
#   protocol          = "HTTP"

#   default_action {
#     type             = "forward"
#     target_group_arn = "${aws_lb_target_group.eugene_search_alb_ip_target_group.arn}"
#   }
#   tags = merge(local.base_tags, {
#     Name = "eugene-search-alb-listener"
#   })
# }