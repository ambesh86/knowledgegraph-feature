# =============================================================================
# EC2 instance running the Next.js UI in Docker, fronted by systemd.
# =============================================================================

# ---------- Security group ----------------------------------------------------
resource "aws_security_group" "ui" {
  name        = "${var.name_prefix}-sg"
  description = "Eugene UI EC2: inbound on UI port + port 80, all egress (needs to reach internal ALB)"
  vpc_id      = var.vpc_id

  ingress {
    description = "UI port (Next.js standalone)"
    from_port   = var.ui_port
    to_port     = var.ui_port
    protocol    = "tcp"
    cidr_blocks = var.allow_ingress_cidrs
  }

  dynamic "ingress" {
    for_each = var.expose_on_port_80 ? [1] : []
    content {
      description = "HTTP (mapped to UI port)"
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = var.allow_ingress_cidrs
    }
  }

  egress {
    description = "all egress (needs ALB + ghcr.io + system updates)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---------- IAM (SSM Session Manager + optional SSM SecureString read) -------
data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ui" {
  name               = "${var.name_prefix}-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ui.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "read_ghcr_secrets" {
  count = local.use_ghcr_login ? 1 : 0
  name  = "${var.name_prefix}-read-ghcr-secrets"
  role  = aws_iam_role.ui.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = ["ssm:GetParameter", "kms:Decrypt"],
      Resource = [
        var.ghcr_username_ssm_arn,
        var.ghcr_token_ssm_arn,
        "*"
      ]
    }]
  })
}

resource "aws_iam_instance_profile" "ui" {
  name = "${var.name_prefix}-profile"
  role = aws_iam_role.ui.name
}

# ---------- User-data: install Docker, pull image, run via systemd -----------
locals {
  # Destinations that must NEVER traverse the proxy.
  #
  # 169.254.169.254 is the one that matters most: IMDS is link-local, a proxy
  # cannot route to it, and when it is proxied the instance role stops resolving.
  # The symptom is "S3 access denied" / "no credentials", which sends people
  # looking at IAM for a day. The ALB and Postgres are in-VPC and would be
  # pointlessly slowed — and possibly blocked — by an external hop.
  no_proxy_base = join(",", compact([
    "localhost",
    "127.0.0.1",
    "169.254.169.254",
    ".internal",
    "10.0.0.0/8",
    "atlas-postgres",
    try(regex("//([^/:]+)", var.eugene_alb_base)[0], ""),
    var.no_proxy_extra,
  ]))

  use_proxy = var.http_proxy_url != ""
  use_ca    = var.corporate_ca_pem != ""

  # Container-name URLs on the shared atlas-net. When a service is disabled the
  # UI is pointed at an address that fails fast rather than left on its
  # docker-compose default, which would resolve to nothing and hang.
  scout_url = var.enable_scout ? "http://eugene-scout:8000" : "http://127.0.0.1:1"
  ade_url   = var.enable_ade ? "http://eugene-ade:8000" : "http://127.0.0.1:1"

  # Postgres data path: the persistent EBS mount when enabled, else a Docker
  # named volume (which does NOT survive instance replacement).
  pg_data_mount = var.persist_atlas_data ? "/mnt/atlas-data/pgdata" : "atlas-pg-data"

  use_ecr      = can(regex("[0-9]+\\.dkr\\.ecr\\.", var.ui_image))
  ecr_registry = local.use_ecr ? split("/", var.ui_image)[0] : ""

  # Passed to `docker run`. Empty string when no proxy is configured, so the
  # generated unit file is byte-identical to the pre-proxy one.
  container_proxy_env = local.use_proxy ? join(" ", [
    "-e HTTP_PROXY=${var.http_proxy_url}",
    "-e HTTPS_PROXY=${var.http_proxy_url}",
    "-e http_proxy=${var.http_proxy_url}",
    "-e https_proxy=${var.http_proxy_url}",
    "-e NO_PROXY=${local.no_proxy_base}",
    "-e no_proxy=${local.no_proxy_base}",
  ]) : ""

  # Node does not read HTTP_PROXY on its own (undici ignores it), so the app also
  # needs the CA mounted and pointed at explicitly.
  container_ca_env = local.use_ca ? join(" ", [
    "-v /etc/pki/ca-trust/source/anchors/corporate.pem:/etc/ssl/corporate.pem:ro",
    "-e NODE_EXTRA_CA_CERTS=/etc/ssl/corporate.pem",
    "-e REQUESTS_CA_BUNDLE=/etc/ssl/corporate.pem",
    "-e SSL_CERT_FILE=/etc/ssl/corporate.pem",
  ]) : ""

  user_data = <<-EOT
    #!/usr/bin/env bash
    set -Eeuo pipefail
    exec > >(tee -a /var/log/eugene-ui-bootstrap.log) 2>&1
    echo "===== $(date -u) bootstrap start ====="

    %{if local.use_ca}
    # ---- Corporate root CA ---------------------------------------------------
    # Installed before anything reaches the network: dnf and docker pull both
    # fail certificate validation without it when egress is TLS-intercepted.
    cat >/etc/pki/ca-trust/source/anchors/corporate.pem <<'CACERT'
    ${var.corporate_ca_pem}
    CACERT
    update-ca-trust extract
    echo "corporate CA installed"
    %{endif}

    %{if local.use_proxy}
    # ---- Proxy, for every consumer that needs it separately ------------------
    # These are three different consumers and configuring one does not configure
    # the others: the shell (operators), the Docker daemon (image pulls), and the
    # containers (the app's own calls, set on the docker run line below).
    cat >/etc/profile.d/corporate-proxy.sh <<'PROXYSH'
    export HTTP_PROXY="${var.http_proxy_url}"
    export HTTPS_PROXY="${var.http_proxy_url}"
    export http_proxy="${var.http_proxy_url}"
    export https_proxy="${var.http_proxy_url}"
    export NO_PROXY="${local.no_proxy_base}"
    export no_proxy="${local.no_proxy_base}"
    PROXYSH
    chmod 0644 /etc/profile.d/corporate-proxy.sh
    source /etc/profile.d/corporate-proxy.sh

    mkdir -p /etc/systemd/system/docker.service.d
    cat >/etc/systemd/system/docker.service.d/http-proxy.conf <<'DOCKERPROXY'
    [Service]
    Environment="HTTP_PROXY=${var.http_proxy_url}"
    Environment="HTTPS_PROXY=${var.http_proxy_url}"
    Environment="NO_PROXY=${local.no_proxy_base}"
    DOCKERPROXY

    # dnf reads its own config, not the environment, when run by cloud-init.
    if ! grep -q '^proxy=' /etc/dnf/dnf.conf; then
      echo "proxy=${var.http_proxy_url}" >> /etc/dnf/dnf.conf
    fi
    %{endif}

    dnf -y update
    dnf -y install docker awscli
    systemctl daemon-reload
    systemctl enable --now docker

    %{if local.use_ghcr_login}
    GHCR_USER=$(aws ssm get-parameter --region ${var.aws_region} \
      --name "$(echo ${var.ghcr_username_ssm_arn} | sed 's|.*parameter||')" \
      --query Parameter.Value --output text)
    GHCR_TOKEN=$(aws ssm get-parameter --region ${var.aws_region} --with-decryption \
      --name "$(echo ${var.ghcr_token_ssm_arn} | sed 's|.*parameter||')" \
      --query Parameter.Value --output text)
    echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin
    %{endif}

    %{if local.use_ecr}
    # ---- ECR login -----------------------------------------------------------
    # ECR is reachable over the VPC's ecr.api/ecr.dkr/s3 endpoints, so image
    # pulls need no internet at all — unlike ghcr.io, which does.
    aws ecr get-login-password --region ${var.aws_region} \
      | docker login --username AWS --password-stdin ${local.ecr_registry}
    %{endif}

    docker pull ${var.ui_image}
    docker pull ${var.postgres_image}

    # Shared network so the UI can reach Postgres by container name.
    docker network create atlas-net || true

    %{if var.persist_atlas_data}
    # ---- Persistent data volume ---------------------------------------------
    # The database lives on a separate EBS volume so that replacing this
    # instance (which every deploy does) does not delete every user account and
    # conversation. Find it by "is a disk, is not the root disk, has no
    # partitions" rather than by device name: Nitro renames /dev/sdf to an
    # nvme* device with no stable ordering.
    for i in $(seq 1 30); do
      DATA_DEV=$(lsblk -dpno NAME,TYPE | awk '$2=="disk"{print $1}' \
        | grep -v "$(findmnt -no SOURCE / | sed 's/p\?[0-9]*$//')" | head -1)
      [ -n "$DATA_DEV" ] && break
      echo "waiting for data volume to attach ($i)..."; sleep 5
    done

    if [ -n "$DATA_DEV" ]; then
      # Format ONLY if there is no filesystem — this must be idempotent, since
      # a re-bootstrap on an existing volume would otherwise wipe it.
      if ! blkid "$DATA_DEV" >/dev/null 2>&1; then
        echo "no filesystem on $DATA_DEV — formatting (first boot)"
        mkfs.ext4 -L atlas-data "$DATA_DEV"
      else
        echo "existing filesystem on $DATA_DEV — preserving data"
      fi
      mkdir -p /mnt/atlas-data
      grep -q '/mnt/atlas-data' /etc/fstab || \
        echo "LABEL=atlas-data /mnt/atlas-data ext4 defaults,nofail 0 2" >> /etc/fstab
      mount -a
      mkdir -p /mnt/atlas-data/pgdata
      chown -R 999:999 /mnt/atlas-data/pgdata   # postgres uid in the official image
      echo "data volume ready at /mnt/atlas-data"
    else
      echo "WARNING: no data volume found; Postgres will use instance storage"
    fi
    %{endif}

    # ---- Atlas Postgres (auth / conversations / messages) --------------------
    # Runs BESIDE the UI on this EC2. Neo4j and all graph data stay in the
    # existing backend behind the ALB — this DB only holds app users + chat
    # history. Data persists in a named volume (survives restarts/reboots).
    cat >/etc/systemd/system/atlas-postgres.service <<'PGUNIT'
    [Unit]
    Description=Atlas Postgres (auth/history)
    Wants=docker.service
    After=docker.service network-online.target

    [Service]
    Restart=always
    RestartSec=5
    ExecStartPre=-/usr/bin/docker network create atlas-net
    ExecStartPre=-/usr/bin/docker rm -f atlas-postgres
    ExecStart=/usr/bin/docker run --rm --name atlas-postgres \
      --network atlas-net \
      -e POSTGRES_USER=atlas \
      -e POSTGRES_PASSWORD=${var.atlas_pg_password} \
      -e POSTGRES_DB=atlas \
      -v ${local.pg_data_mount}:/var/lib/postgresql/data \
      ${var.postgres_image}
    ExecStop=/usr/bin/docker stop atlas-postgres

    [Install]
    WantedBy=multi-user.target
    PGUNIT

    %{if var.enable_scout}
    # ---- Eugene Scout (Radar / Watchlist / Today / Briefing) -----------------
    # Not a duplicate of the prod backend: there is no scout anywhere in the ECS
    # cluster, so without this the Radar has nothing to call and every one of
    # those four screens renders its degraded state. Scanning needs outbound
    # internet; if egress is closed the service still runs and reports degraded,
    # which is the honest failure rather than a blank page.
    docker pull ${var.scout_image}
    cat >/etc/systemd/system/eugene-scout.service <<'SCOUTUNIT'
    [Unit]
    Description=Eugene Scout (competitive signal scanner)
    Wants=docker.service
    After=docker.service network-online.target

    [Service]
    Restart=always
    RestartSec=10
    ExecStartPre=-/usr/bin/docker network create atlas-net
    ExecStartPre=-/usr/bin/docker rm -f eugene-scout
    ExecStart=/usr/bin/docker run --rm --name eugene-scout \
      --network atlas-net \
      -e SCOUT_S3_BUCKET=${var.scout_s3_bucket} \
      -e AWS_REGION=${var.aws_region} \
      -e SCOUT_API_TOKEN=${var.scout_api_token} \
      -e SCOUT_SCAN_ENABLED=${var.scout_scan_enabled ? "true" : "false"} \
      -e SCOUT_INDEX_REFRESH_MINUTES=${var.index_refresh_minutes} \
      ${local.container_proxy_env} \
      ${local.container_ca_env} \
      ${var.scout_image}
    ExecStop=/usr/bin/docker stop eugene-scout

    [Install]
    WantedBy=multi-user.target
    SCOUTUNIT
    %{endif}

    %{if var.enable_ade}
    # ---- Eugene ADE (document extraction / evidence rendering) ---------------
    # Backs every "Source evidence" link. Without it the evidence pages 502.
    # Memory-hungry when the layout model loads (~40MB weights + OpenCV), which
    # is why instance_type must be at least t3.large when this is enabled.
    docker pull ${var.ade_image}
    cat >/etc/systemd/system/eugene-ade.service <<'ADEUNIT'
    [Unit]
    Description=Eugene ADE (agentic document extraction)
    Wants=docker.service
    After=docker.service network-online.target

    [Service]
    Restart=always
    RestartSec=10
    ExecStartPre=-/usr/bin/docker network create atlas-net
    ExecStartPre=-/usr/bin/docker rm -f eugene-ade
    ExecStart=/usr/bin/docker run --rm --name eugene-ade \
      --network atlas-net \
      -e ADE_S3_BUCKET=${var.ade_s3_bucket} \
      -e AWS_REGION=${var.aws_region} \
      -e ADE_LAYOUT_ENABLED=${var.ade_layout_enabled ? "true" : "false"} \
      -e ADE_INGEST_ENABLED=${var.ade_ingest_enabled ? "true" : "false"} \
      -v eugene_ade_models:/root/.cache \
      ${local.container_proxy_env} \
      ${local.container_ca_env} \
      ${var.ade_image}
    ExecStop=/usr/bin/docker stop eugene-ade

    [Install]
    WantedBy=multi-user.target
    ADEUNIT
    %{endif}

    # ---- Eugene Next.js UI ---------------------------------------------------
    # systemd unit: keeps the UI running across reboots and across re-deploys
    cat >/etc/systemd/system/eugene-ui.service <<'UNIT'
    [Unit]
    Description=Eugene Next.js UI
    Wants=docker.service atlas-postgres.service
    After=docker.service network-online.target atlas-postgres.service

    [Service]
    Restart=always
    RestartSec=5
    ExecStartPre=-/usr/bin/docker network create atlas-net
    ExecStartPre=-/usr/bin/docker rm -f eugene-ui
    ExecStartPre=/usr/bin/docker pull ${var.ui_image}
    ExecStart=/usr/bin/docker run --rm --name eugene-ui \
      --network atlas-net \
      -p ${var.expose_on_port_80 ? "80" : tostring(var.ui_port)}:${var.ui_port} \
      -e NODE_ENV=production \
      -e NODE_TLS_REJECT_UNAUTHORIZED=${var.skip_alb_tls_verify ? "0" : "1"} \
      -e EUGENE_CORE_API_URL=${var.eugene_alb_base} \
      -e EUGENE_AGENT_API_URL=${var.eugene_agent_api_url} \
      -e EUGENE_MCP_SERVER_URL=${var.eugene_mcp_url} \
      -e ATLAS_DATABASE_URL=postgres://atlas:${var.atlas_pg_password}@atlas-postgres:5432/atlas \
      -e ATLAS_JWT_SECRET=${var.atlas_jwt_secret} \
      -e OPENAI_API_KEY=${var.openai_api_key} \
      -e EUGENE_SCOUT_URL=${local.scout_url} \
      -e SCOUT_API_TOKEN=${var.scout_api_token} \
      -e EUGENE_ADE_URL=${local.ade_url} \
      ${local.container_proxy_env} \
      ${local.container_ca_env} \
      ${var.ui_image}
    ExecStop=/usr/bin/docker stop eugene-ui

    [Install]
    WantedBy=multi-user.target
    UNIT

    systemctl daemon-reload
    systemctl enable --now atlas-postgres.service
    %{if var.enable_scout}
    systemctl enable --now eugene-scout.service
    %{endif}
    %{if var.enable_ade}
    systemctl enable --now eugene-ade.service
    %{endif}
    systemctl enable --now eugene-ui.service
    echo "===== bootstrap done ====="
  EOT
}

# ---------- The EC2 instance --------------------------------------------------
resource "aws_instance" "ui" {
  ami                         = local.ami_id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [aws_security_group.ui.id]
  iam_instance_profile        = aws_iam_instance_profile.ui.name
  associate_public_ip_address = var.associate_public_ip
  key_name                    = var.key_name == "" ? null : var.key_name
  user_data                   = local.user_data
  # A user_data change must RE-BOOTSTRAP the box (install Postgres + inject the
  # Atlas env), so force a replacement rather than a no-op in-place update.
  user_data_replace_on_change = true

  metadata_options {
    http_tokens                 = "required" # IMDSv2 only
    http_endpoint               = "enabled"
    http_put_response_hop_limit = 2 # allow docker → IMDS
  }

  root_block_device {
    volume_size = var.root_volume_gb
    volume_type = "gp3"
    encrypted   = true
  }

  tags = { Name = "${var.name_prefix}-instance" }

  lifecycle {
    ignore_changes = [ami]
  }
}

# ---------- Optional Elastic IP for stable public access ---------------------
resource "aws_eip" "ui" {
  count    = var.associate_public_ip ? 1 : 0
  instance = aws_instance.ui.id
  domain   = "vpc"
  tags     = { Name = "${var.name_prefix}-eip" }
}

# ---------- Deploy-time guards ------------------------------------------------
# Checked at plan time, so a misconfiguration fails before it reaches the box
# rather than after, as a container that will not start.
check "deployment_readiness" {
  assert {
    condition     = !var.enable_ade || contains(["t3.large", "t3.xlarge", "t3.2xlarge", "m5.large", "m5.xlarge"], var.instance_type)
    error_message = "enable_ade needs at least t3.large — the layout model plus OpenCV will not fit beside the UI and Postgres on ${var.instance_type}."
  }
  assert {
    condition     = !var.enable_scout || var.scout_image != ""
    error_message = "enable_scout is true but scout_image is empty. Build and push the scanner image first."
  }
  assert {
    condition     = !var.enable_ade || var.ade_image != ""
    error_message = "enable_ade is true but ade_image is empty. Build and push the ADE image first."
  }
  assert {
    condition     = !var.enable_scout || var.scout_s3_bucket != ""
    error_message = "enable_scout needs scout_s3_bucket — the scanner persists signals to S3."
  }
  assert {
    condition     = var.persist_atlas_data
    error_message = "persist_atlas_data is false: this deploy replaces the instance and will DELETE all users and conversation history."
  }
}
