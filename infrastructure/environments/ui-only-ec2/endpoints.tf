# =============================================================================
# VPC interface endpoints.
#
# This VPC reaches AWS services in one of two ways: through a VPC endpoint, or
# through the internet. It has no internet. So every AWS service without an
# endpoint here is simply unreachable from this instance — which is not a
# firewall problem and will never be fixed by one.
#
# Present already (verified 2026-08-15): ec2, ecr.api, ecr.dkr, s3 (gateway),
# elasticloadbalancing, codedeploy, codedeploy-commands-secure, email-smtp.
# Conspicuously absent: ssm, ssmmessages, ec2messages — hence no Session Manager.
# =============================================================================

# bedrock-runtime is NOT declared here — bedrock.tf already owns it, gated on
# var.enable_bedrock. One endpoint, one owner.
locals {
  ssm_endpoint_services = concat(
    var.enable_ssm_endpoints ? [
      "ssm",         # the API itself
      "ssmmessages", # Session Manager data channel — the one people forget
      "ec2messages", # agent <-> service messaging
    ] : [],
    var.additional_interface_endpoints,
  )

  want_endpoint_sg = length(local.ssm_endpoint_services) > 0
}

# Endpoints are reached over 443 from inside the VPC, so they need a security
# group that admits the instance. Separate from the instance SG: an endpoint is
# infrastructure shared by anything in the VPC, not part of the UI's identity.
resource "aws_security_group" "endpoints" {
  count       = local.want_endpoint_sg ? 1 : 0
  name        = "${var.name_prefix}-vpce-sg"
  description = "HTTPS from the VPC to interface endpoints"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTPS from within the VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.this.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_vpc" "this" {
  id = var.vpc_id
}

resource "aws_vpc_endpoint" "ssm" {
  for_each            = toset(local.ssm_endpoint_services)
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.${each.value}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [var.subnet_id]
  security_group_ids  = [aws_security_group.endpoints[0].id]
  private_dns_enabled = true

  tags = { Name = "${var.name_prefix}-vpce-${each.value}" }
}
