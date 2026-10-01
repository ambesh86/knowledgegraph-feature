resource "aws_lb_target_group" "eugene_search_alb_ip_target_group" {
  name        = "${var.resource_prefix}-eugene-search-lb-tg"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    enabled             = true
    interval            = 30
    path                = "/health"
    port                = "8000"
    protocol            = "HTTP"
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 5
    matcher             = "200"
  }

  tags = merge(var.base_tags, {
    Name = "${var.resource_prefix}-eugene-search-lb-tg"
    workloadName = var.workload_name
  })

}
