# =============================================================================
# Inputs for the UI-only EC2 deploy.
# The EC2 must live in the SAME VPC as the internal ALB
# (internal-eugene-search-alb-...elb.amazonaws.com) so it can reach the
# Eugene agent + core APIs.
# =============================================================================

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "name_prefix" {
  type    = string
  default = "eugene-ui"
  validation {
    condition     = can(regex("^[a-z0-9-]{3,24}$", var.name_prefix))
    error_message = "name_prefix must be lowercase alphanumeric + dashes, 3..24 chars."
  }
}

# ---------------------------- Network ----------------------------------------

variable "vpc_id" {
  description = "VPC ID that hosts the internal Eugene ALB."
  type        = string
}

variable "subnet_id" {
  description = <<EOT
Subnet to place the EC2 in. Must be in the same VPC as the ALB.
- For browser access from the office: pick a PUBLIC subnet (route table has
  an IGW). EIP will be attached.
- For browser access from the corporate network only: pick a PRIVATE subnet
  with VPN reachability. Set associate_public_ip=false.
EOT
  type        = string
}

variable "associate_public_ip" {
  description = "If true, attach an Elastic IP and allow inbound from allow_ingress_cidrs."
  type        = bool
  default     = true
}

variable "allow_ingress_cidrs" {
  description = "CIDR blocks allowed to reach the UI port. Restrict to your office IP or VPN range."
  type        = list(string)
  default     = ["0.0.0.0/0"] # CHANGE THIS for production
}

# ---------------------------- EC2 sizing -------------------------------------

variable "instance_type" {
  description = "EC2 instance size. t3.small handles the Next.js SSR for a small team."
  type        = string
  default     = "t3.small"
}

variable "ami_id" {
  description = "AMI to use. Empty = latest Amazon Linux 2023 (looked up dynamically)."
  type        = string
  default     = ""
}

variable "root_volume_gb" {
  type    = number
  default = 30
}

variable "key_name" {
  description = "Optional EC2 key pair name for SSH. Leave empty to use SSM Session Manager only (recommended)."
  type        = string
  default     = ""
}

# ---------------------------- UI image ---------------------------------------

variable "ui_image" {
  description = <<EOT
Full image reference for the eugene-agent-ui-next image.
Defaults to the ghcr.io repo that .github/workflows/build-images.yml publishes.
EOT
  type        = string
  default     = "ghcr.io/aisemanticexpert/eugene-agent-ui-next:latest"
}

variable "ui_port" {
  description = "Port the Next.js standalone server listens on (matches package.json: next start -p 18502)."
  type        = number
  default     = 18502
}

variable "expose_on_port_80" {
  description = "If true, also map host :80 → container :18502 so users can hit the EC2 without specifying a port."
  type        = bool
  default     = true
}

# Registry auth — only needed for PRIVATE ghcr.io images.
# Create a GitHub PAT with `read:packages` scope and put it (and your username)
# into SSM Parameter Store, then set both ARNs here.
variable "ghcr_username_ssm_arn" {
  description = "Optional. SSM Parameter ARN holding your GitHub username (plain String)."
  type        = string
  default     = ""
}

variable "ghcr_token_ssm_arn" {
  description = "Optional. SSM Parameter ARN holding the read:packages PAT (SecureString)."
  type        = string
  default     = ""
}

# ---------------------------- TLS posture toward backend ALB -----------------

variable "skip_alb_tls_verify" {
  description = <<EOT
If true, the UI process (Node.js) is started with NODE_TLS_REJECT_UNAUTHORIZED=0,
which disables TLS certificate verification on outbound calls. Required when
the internal ALB serves a self-signed certificate (as the current CSL DiffLabs
dev ALB does: CN=eugene-development.ai.cslg1.cslg.net, self-issued).
Set back to false once the ALB gets a properly issued cert and trust it via
NODE_EXTRA_CA_CERTS instead.
EOT
  type        = bool
  default     = true
}

# ---------------------------- Backend endpoints ------------------------------
# These match the values you supplied. Keep them in one place so a change to
# the ALB hostname is a one-line edit.

variable "eugene_alb_base" {
  type    = string
  default = "https://internal-eugene-search-alb-616664632.us-east-1.elb.amazonaws.com"
}

variable "eugene_mcp_url" {
  type    = string
  default = "https://internal-eugene-search-alb-616664632.us-east-1.elb.amazonaws.com:8443/mcp"
}

variable "eugene_agent_api_url" {
  description = "Base URL the UI uses to reach the agent (the UI appends /query/stream itself in some routes)."
  type        = string
  default     = "https://internal-eugene-search-alb-616664632.us-east-1.elb.amazonaws.com/agent/api"

  # app/api/stream/route.ts does fetch(`${agentApi}/query/stream`). Passing the
  # full endpoint yields ".../query/stream/query/stream" and every question 404s
  # — which reads as a backend outage rather than a config typo, so it is worth
  # refusing at plan time.
  validation {
    condition     = !can(regex("/query/stream", var.eugene_agent_api_url))
    error_message = "eugene_agent_api_url must be the BASE (e.g. https://<alb>/agent/api). The UI appends /query/stream itself."
  }

  # Shell-style interpolation does not expand in Terraform or `docker run -e`;
  # it is passed through literally and the backend then rejects every token.
  validation {
    condition     = !can(regex("\\$\\{", var.eugene_agent_api_url))
    error_message = "Literal $${...} found — Terraform does not expand shell interpolation. Write the resolved value."
  }
}

# ---------------------------- Atlas app (auth / history / digest) ------------
# The CSL Atlas UI stores users, conversations and messages in its OWN Postgres.
# Option A runs that Postgres as a SECOND container on this same EC2 (Neo4j and
# all graph data stay in the existing backend behind the ALB — untouched).

variable "postgres_image" {
  description = "Postgres image for the Atlas auth/history DB (runs beside the UI)."
  type        = string
  default     = "postgres:16-alpine"
}

variable "atlas_pg_password" {
  description = "Password for the Atlas Postgres 'atlas' user."
  type        = string
  default     = "atlas_local_2026"
  sensitive   = true
}

variable "atlas_jwt_secret" {
  # This is also the key-encryption key for the stored EUGENE_CLIENT_SECRET, so a
  # placeholder here is both a security hole and a future decryption failure.
  validation {
    condition     = length(var.atlas_jwt_secret) >= 32 && !can(regex("(?i)change-me", var.atlas_jwt_secret))
    error_message = "atlas_jwt_secret must be >= 32 chars and must not contain 'change-me'."
  }
  description = "Secret used to sign Atlas session JWTs. CHANGE for production (32+ chars)."
  type        = string
  default     = "change-me-atlas-prod-secret-32chars-min"
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI key used ONLY for LLM conversation titling. Empty = heuristic titles."
  type        = string
  default     = ""
  sensitive   = true
}

# ---------------------------- TLS / public ALB (optional) -------------------

variable "enable_tls" {
  description = "If true, create a public ALB + ACM cert + Route 53 record fronting the EC2."
  type        = bool
  default     = false
}

variable "domain_name" {
  description = "Hostname the UI will serve at, e.g. 'eugene.yourcorp.com'. Required when enable_tls=true."
  type        = string
  default     = ""
  validation {
    condition     = var.enable_tls == false || length(var.domain_name) > 0
    error_message = "domain_name is required when enable_tls = true."
  }
}

variable "route53_zone_id" {
  description = "Route 53 hosted zone ID that owns domain_name (used for DNS-01 validation and the alias record). Required when enable_tls=true."
  type        = string
  default     = ""
  validation {
    condition     = var.enable_tls == false || length(var.route53_zone_id) > 0
    error_message = "route53_zone_id is required when enable_tls = true."
  }
}

variable "alb_public_subnet_ids" {
  description = "Public subnet IDs (with IGW route) for the public ALB. At least 2 in different AZs. Required when enable_tls=true."
  type        = list(string)
  default     = []
  validation {
    condition     = var.enable_tls == false || length(var.alb_public_subnet_ids) >= 2
    error_message = "Provide at least 2 public subnets in different AZs when enable_tls = true."
  }
}

variable "alb_public_allow_cidrs" {
  description = "CIDRs allowed to reach the public ALB (browsers). Use [\"0.0.0.0/0\"] only if the UI is meant for the open internet."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "common_tags" {
  type = map(string)
  default = {
    workload   = "eugene"
    component  = "ui-next"
    managed_by = "terraform"
  }
}

# Mandatory governance tags enforced by the CSL org SCP (Deny* statements on
# ec2:RunInstances). Every key here must be present on the create request or the
# launch is explicitly denied. Values copied from the compliant Eugene backend
# instance (euGENE-1). Override per-workload as needed.
variable "governance_tags" {
  type = map(string)
  default = {
    workloadName        = "EUGENE"
    workloadOwner       = "sterling.foster@cslbehring.com"
    workloadEnvironment = "d1"
    costCenter          = "4520450000"
    businessUnit        = "Information and Technology"
    technicalOwner      = "sterling.foster@cslbehring.com"
    APM                 = "APM0007514"
    dataClassification  = "Proprietary"
  }
}

# ---------------------------- Corporate egress -------------------------------
# This VPC has NO internet gateway and NO NAT gateway. The subnet's default route
# is 0.0.0.0/0 -> tgw-0122884db8995c4d1, so every packet bound for the internet
# leaves AWS and is decided by the corporate egress stack. Nothing that can be
# changed inside this account — security group, NACL, route table — affects that
# decision; all three are already fully open (verified 2026-08-15).
#
# Two consequences, and these variables cover both:
#
#  1. If corporate egress is proxy-only (the usual arrangement, and the reason
#     the VDI works — the VDI has proxy settings and the corporate CA, this box
#     has neither), the application must be *told* about the proxy. Direct
#     connections do not fall back to it.
#  2. If that proxy terminates TLS, every client also needs the corporate root
#     CA, or every HTTPS call fails certificate validation even though the
#     network is working perfectly.

variable "http_proxy_url" {
  description = <<EOT
Corporate forward proxy, e.g. "http://proxy.corp.example:8080". Empty (default)
leaves the instance configured for direct egress, exactly as before — so setting
this is opt-in and changes nothing until you have a real proxy address.

When set it is applied in three places, all of which are required and none of
which imply the others:
  * the Docker daemon (so `docker pull` of the UI image works at boot),
  * the container environment (so the Node.js app's own outbound calls work),
  * the shell profile (so an operator debugging on the box sees the same path).
EOT
  type        = string
  default     = ""
}

variable "no_proxy_extra" {
  description = <<EOT
Extra comma-separated hosts/CIDRs that must NOT go through the proxy, appended to
the mandatory set. The mandatory set already includes 169.254.169.254 — sending
IMDS to a proxy silently destroys the instance role, and therefore S3 and every
other AWS call, in a way that looks like an IAM problem rather than a proxy one.
EOT
  type        = string
  default     = ""
}

variable "corporate_ca_pem" {
  description = <<EOT
PEM-encoded corporate root CA, for the case where the proxy intercepts TLS.
Installed into the OS trust store and mounted into the containers, with
NODE_EXTRA_CA_CERTS / REQUESTS_CA_BUNDLE / SSL_CERT_FILE pointed at it.

Prefer passing via TF_VAR_corporate_ca_pem or -var-file rather than committing.
Empty (default) skips all CA handling.
EOT
  type        = string
  default     = ""
  sensitive   = true
}

variable "enable_ssm_endpoints" {
  description = <<EOT
Create the three interface endpoints Session Manager needs (ssm, ssmmessages,
ec2messages). This VPC has none of them and no internet path, which is exactly
why `aws ssm start-session` does not work today and why deploys are done by
rebooting the box.

Roughly USD 22/month for the three endpoint ENIs. Worth it: without a shell you
cannot run bin/aws/egress-doctor.sh, and without that you are negotiating with
the network team from assertion rather than evidence.
EOT
  type        = bool
  default     = false
}


variable "additional_interface_endpoints" {
  description = <<EOT
Extra AWS service names to expose as interface endpoints, e.g.
["secretsmanager"]. Note that bedrock.tf's enable_onbox_backend grants the
instance role secretsmanager:GetSecretValue, but this VPC has no
secretsmanager endpoint and no internet — so that fetch cannot currently
succeed. Add "secretsmanager" here to close that gap.

Do not list "bedrock-runtime": bedrock.tf owns it via enable_bedrock.
EOT
  type        = list(string)
  default     = []
}

# ---------------------------- Data persistence -------------------------------

variable "persist_atlas_data" {
  description = <<EOT
Keep the Atlas database (users, conversations, messages) on a dedicated EBS
volume instead of the instance root disk.

Strongly recommended, and effectively required for a real deployment: every
deploy replaces the instance (user_data_replace_on_change), and a Docker named
volume on the root disk dies with it. Without this, shipping a new UI image
silently deletes every account and every conversation.
EOT
  type        = bool
  default     = true
}

variable "atlas_data_volume_gb" {
  description = "Size of the persistent Postgres volume."
  type        = number
  default     = 20
}

# ---------------------------- Scout / ADE services ---------------------------
# Neither of these exists anywhere in the AWS account today. The UI therefore
# falls back to its docker-compose defaults (http://eugene_scout:8000), which do
# not resolve on the instance — so Radar, Watchlist, Today, Briefing and every
# Evidence page are broken on AWS regardless of networking. Running them beside
# the UI is the smallest change that makes those screens work.

variable "enable_scout" {
  description = "Run the Scout scanner container (backs Radar/Watchlist/Today/Briefing)."
  type        = bool
  default     = true
}

variable "scout_image" {
  description = "Scout container image. Push to ECR so the pull needs no internet."
  type        = string
  default     = ""
}

variable "scout_s3_bucket" {
  description = "Bucket for scanner state and scored signals."
  type        = string
  default     = ""
}

variable "scout_api_token" {
  description = "Shared secret between the UI and the scanner API. Empty = unauthenticated."
  type        = string
  default     = ""
  sensitive   = true
}

variable "enable_ade" {
  description = <<EOT
Run the ADE document-extraction container (backs every "Source evidence" link).
Requires at least t3.large: the layout model plus OpenCV will not fit beside the
UI and Postgres on a t3.medium.
EOT
  type        = bool
  default     = true
}

variable "ade_image" {
  description = "ADE container image."
  type        = string
  default     = ""
}

variable "ade_s3_bucket" {
  description = "Bucket for extracted PDFs and artifacts."
  type        = string
  default     = "eugene-research-pdfs-087084717211"
}

variable "ade_layout_enabled" {
  description = "Load DocLayout-YOLO for semantic region labels. false = structural labels only, much lighter."
  type        = bool
  default     = true
}

# ---------------------------- Split deployment -------------------------------
# An SCP denies internet gateways account-wide, so nothing deployed in AWS can
# reach ClinicalTrials.gov, Europe PMC, NCBI, USPTO or SEC — and no permission
# level changes that. But S3 is reachable over a gateway endpoint, and both
# Scout and ADE separate cleanly into a half that needs the internet (scan,
# ingest) and a half that only needs S3 (serve).
#
# So the fetching runs where internet exists (a VDI, a CI runner) and writes to
# S3; this deployment serves what it finds there. Users get the full product
# from a shared, always-on host, and freshness is bounded by when the fetcher
# last ran — which the "as of" indicator already shows.

variable "scout_scan_enabled" {
  description = <<EOT
Whether THIS instance performs scans. Default false, because this instance is
in AWS and AWS has no egress. Set true only where the internet is reachable.

When false the service registers no scan cron, refuses POST /scan with an
explanation, and instead re-reads the curated index from S3 on a timer.
EOT
  type        = bool
  default     = false
}

variable "ade_ingest_enabled" {
  description = <<EOT
Whether THIS instance fetches and extracts new PDFs. Default false for the same
reason. Evidence rendering is unaffected — page images are rebuilt from the
grounding data and PDF already in S3, so every citation stays provable.
EOT
  type        = bool
  default     = false
}

variable "index_refresh_minutes" {
  description = "How often a serve-only Scout re-reads the curated index from S3."
  type        = number
  default     = 10
}
