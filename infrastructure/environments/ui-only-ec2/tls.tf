# =============================================================================
# Optional HTTPS front door: public ALB + ACM cert (DNS-validated via Route 53)
# Enable with `enable_tls = true` and supply `domain_name` + `route53_zone_id`.
#
# When enabled, this stack creates:
#   - aws_acm_certificate     (issued + auto-validated via R53)
#   - aws_lb                  (public ALB)
#   - aws_lb_target_group     (points at the EC2)
#   - aws_lb_target_group_attachment   (registers the EC2)
#   - aws_lb_listener  :443   (HTTPS, with the cert)
#   - aws_lb_listener  :80    (HTTP → HTTPS redirect)
#   - aws_route53_record      (the A-alias to the ALB)
#   - aws_security_group ingress rule allowing the ALB SG to reach the EC2
#
# When `enable_tls = false` (default), none of these are created — you keep
# the simple EC2 + EIP path.
# =============================================================================

# ---------- Cert -------------------------------------------------------------
resource "aws_acm_certificate" "ui" {
  count             = var.enable_tls ? 1 : 0
  domain_name       = var.domain_name
  validation_method = "DNS"
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "cert_validation" {
  for_each = var.enable_tls ? {
    for dvo in aws_acm_certificate.ui[0].domain_validation_options :
    dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}
  zone_id = var.route53_zone_id
  name    = each.value.name
  type    = each.value.type
  ttl     = 60
  records = [each.value.record]
}

resource "aws_acm_certificate_validation" "ui" {
  count                   = var.enable_tls ? 1 : 0
  certificate_arn         = aws_acm_certificate.ui[0].arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}

# ---------- Public-facing ALB ------------------------------------------------
resource "aws_security_group" "public_alb" {
  count       = var.enable_tls ? 1 : 0
  name        = "${var.name_prefix}-public-alb-sg"
  description = "Public ALB fronting the Eugene UI"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTPS from allowed CIDRs"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.alb_public_allow_cidrs
  }
  ingress {
    description = "HTTP (will be redirected to HTTPS)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.alb_public_allow_cidrs
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb" "public" {
  count                      = var.enable_tls ? 1 : 0
  name                       = "${var.name_prefix}-public-alb"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.public_alb[0].id]
  subnets                    = var.alb_public_subnet_ids
  drop_invalid_header_fields = true
  enable_deletion_protection = false
}

resource "aws_lb_target_group" "ui" {
  count       = var.enable_tls ? 1 : 0
  name        = substr("${var.name_prefix}-ui-tg", 0, 32)
  port        = var.ui_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "instance"

  health_check {
    enabled             = true
    path                = "/"
    matcher             = "200-399"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_target_group_attachment" "ui" {
  count            = var.enable_tls ? 1 : 0
  target_group_arn = aws_lb_target_group.ui[0].arn
  target_id        = aws_instance.ui.id
  port             = var.ui_port
}

resource "aws_lb_listener" "https" {
  count             = var.enable_tls ? 1 : 0
  load_balancer_arn = aws_lb.public[0].arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.ui[0].certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ui[0].arn
  }
}

resource "aws_lb_listener" "http_redirect" {
  count             = var.enable_tls ? 1 : 0
  load_balancer_arn = aws_lb.public[0].arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type = "redirect"
    redirect {
      protocol    = "HTTPS"
      port        = "443"
      status_code = "HTTP_301"
    }
  }
}

# ---------- Friendly DNS name ------------------------------------------------
resource "aws_route53_record" "ui" {
  count   = var.enable_tls ? 1 : 0
  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"
  alias {
    name                   = aws_lb.public[0].dns_name
    zone_id                = aws_lb.public[0].zone_id
    evaluate_target_health = true
  }
}

# ---------- Allow the public ALB SG → EC2 on the UI port --------------------
# When TLS is enabled, traffic comes from the ALB, not from arbitrary CIDRs.
# We attach a separate rule rather than rewriting the existing SG so toggling
# `enable_tls` is non-destructive.
resource "aws_security_group_rule" "ec2_from_alb" {
  count                    = var.enable_tls ? 1 : 0
  type                     = "ingress"
  description              = "Public ALB to UI port"
  from_port                = var.ui_port
  to_port                  = var.ui_port
  protocol                 = "tcp"
  security_group_id        = aws_security_group.ui.id
  source_security_group_id = aws_security_group.public_alb[0].id
}
