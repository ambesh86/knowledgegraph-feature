# =============================================================================
# Application Load Balancer + target groups + listener rules (one per service)
# =============================================================================

resource "aws_lb" "main" {
  name                       = "${var.name_prefix}-alb"
  internal                   = var.alb_internal
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = var.public_subnet_ids
  drop_invalid_header_fields = true
  enable_deletion_protection = false  # flip to true for prod
}

# One target group per service. ECS will register tasks here.
resource "aws_lb_target_group" "svc" {
  for_each    = toset(local.services)
  name        = substr("${var.name_prefix}-${replace(each.value, "_", "-")}-tg", 0, 32)
  port        = local.container_ports[each.value]
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"  # required for Fargate

  health_check {
    enabled             = true
    path                = each.value == "eugene_agent_ui" ? "/" : (each.value == "eugene_agent_ui_next" ? "/" : "/health")
    matcher             = "200-399"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ---------- HTTPS listener (preferred) ---------------------------------------
resource "aws_lb_listener" "https" {
  count             = var.alb_certificate_arn == "" ? 0 : 1
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.alb_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.svc["eugene_agent_ui_next"].arn
  }
}

# ---------- HTTP listener (lab mode, when no cert) ---------------------------
resource "aws_lb_listener" "http" {
  count             = var.alb_certificate_arn == "" ? 1 : 0
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.svc["eugene_agent_ui_next"].arn
  }
}

locals {
  # Pick whichever listener was created.
  active_listener_arn = var.alb_certificate_arn == "" ? aws_lb_listener.http[0].arn : aws_lb_listener.https[0].arn
}

# ---------- Path-based routing rules -----------------------------------------
resource "aws_lb_listener_rule" "svc" {
  for_each     = { for s in local.services : s => s if s != "eugene_agent_ui_next" }
  listener_arn = local.active_listener_arn
  priority     = local.alb_listener_priority[each.value]

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.svc[each.value].arn
  }

  condition {
    path_pattern {
      values = local.path_patterns[each.value]
    }
  }
}
