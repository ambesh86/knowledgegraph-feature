# =============================================================================
# Graph-only, no-internet LLM path.
#
# The VPC has a filtered egress allowlist (package registries + AWS services
# reachable; general internet — OpenAI, PubMed, public Bedrock endpoint — is
# blocked). So the on-box agent uses Amazon Bedrock (Nova) as its brain,
# reached PRIVATELY via a bedrock-runtime interface VPC endpoint and
# authenticated by the instance role (no API key, no internet).
#
# Toggle with enable_bedrock=false to remove both the endpoint and the IAM
# grant (e.g. if you later move to an internal LLM or add general egress).
# =============================================================================

variable "enable_bedrock" {
  description = "Create the bedrock-runtime VPC endpoint + grant the instance role InvokeModel (Nova)."
  type        = bool
  default     = true
}

variable "bedrock_model_arns" {
  description = "Bedrock foundation-model ARNs the instance may invoke. Defaults to the Amazon Nova family (the only models enabled in this account)."
  type        = list(string)
  default = [
    "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-pro-v1:0",
    "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0",
    "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-2-lite-v1:0",
    "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-micro-v1:0",
  ]
}

# ---------- IAM: let the instance role invoke Bedrock Nova --------------------
resource "aws_iam_role_policy" "bedrock_invoke" {
  count = var.enable_bedrock ? 1 : 0
  name  = "${var.name_prefix}-bedrock-invoke"
  role  = aws_iam_role.ui.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect   = "Allow",
      Action   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      Resource = var.bedrock_model_arns
    }]
  })
}

# ---------- Security group for the interface endpoint (443 from the UI box) ---
resource "aws_security_group" "bedrock_vpce" {
  count       = var.enable_bedrock ? 1 : 0
  name        = "${var.name_prefix}-bedrock-vpce-sg"
  description = "Allow HTTPS from the UI/agent instance to the bedrock-runtime endpoint"
  vpc_id      = var.vpc_id

  ingress {
    description     = "HTTPS from the UI/agent EC2"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.ui.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---------- The private bedrock-runtime endpoint (PrivateLink) ----------------
# private_dns_enabled makes bedrock-runtime.us-east-1.amazonaws.com resolve to
# this endpoint's private IP from the instance — so boto3 (Strands) reaches
# Bedrock without any internet route.
resource "aws_vpc_endpoint" "bedrock_runtime" {
  count               = var.enable_bedrock ? 1 : 0
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.bedrock-runtime"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [var.subnet_id]
  security_group_ids  = [aws_security_group.bedrock_vpce[0].id]
  private_dns_enabled = true

  tags = { Name = "${var.name_prefix}-bedrock-runtime-vpce" }
}

output "bedrock_vpce_id" {
  value       = try(aws_vpc_endpoint.bedrock_runtime[0].id, null)
  description = "ID of the bedrock-runtime interface VPC endpoint (null if disabled)."
}

# =============================================================================
# On-box backend (agent + MCP) needs the Eugene JWT signing secret to VERIFY
# incoming tokens (HS256 with EUGENE_CLIENT_SECRET) and the issuer/audience.
# These live in Secrets Manager; grant the instance role read access so the box
# fetches them itself at deploy time (the value never leaves the instance).
# =============================================================================

variable "enable_onbox_backend" {
  description = "Grant the instance role read access to the Eugene backend secret (agent/MCP run on the box)."
  type        = bool
  default     = true
}

variable "eugene_backend_secret_name" {
  description = "Secrets Manager secret holding EUGENE_CLIENT_SECRET/ISSUER/AUDIENCE/CLIENT_ID (per eugene-mcp fetch_secrets.py)."
  type        = string
  default     = "eugene/dev/uspto/env"
}

resource "aws_iam_role_policy" "read_eugene_secret" {
  count = var.enable_onbox_backend ? 1 : 0
  name  = "${var.name_prefix}-read-eugene-secret"
  role  = aws_iam_role.ui.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = ["secretsmanager:GetSecretValue"],
        Resource = ["arn:aws:secretsmanager:${var.aws_region}:*:secret:${var.eugene_backend_secret_name}-*"]
      },
      {
        Effect   = "Allow",
        Action   = ["kms:Decrypt"],
        Resource = ["*"]
      }
    ]
  })
}
