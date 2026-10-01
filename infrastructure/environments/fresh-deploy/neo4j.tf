# =============================================================================
# Neo4j single-node EC2 with persistent EBS volume.
# For HA / cluster mode swap this for the Neo4j AuraDB managed service or a 3-
# node ASG. Single-node is perfectly fine for staging + dev.
# =============================================================================

resource "aws_iam_role" "neo4j" {
  name               = "${var.name_prefix}-neo4j-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = { Service = "ec2.amazonaws.com" },
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "neo4j_ssm" {
  role       = aws_iam_role.neo4j.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "neo4j_read_ssm" {
  name = "${var.name_prefix}-neo4j-read-secret"
  role = aws_iam_role.neo4j.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect   = "Allow",
      Action   = ["ssm:GetParameter", "kms:Decrypt"],
      Resource = [aws_ssm_parameter.neo4j_password.arn, "*"]
    }]
  })
}

resource "aws_iam_instance_profile" "neo4j" {
  name = "${var.name_prefix}-neo4j-profile"
  role = aws_iam_role.neo4j.name
}

# Persistent data volume (separate from root so we can keep data through
# instance replacements).
resource "aws_ebs_volume" "neo4j_data" {
  availability_zone = data.aws_subnet.first.availability_zone
  size              = var.neo4j_data_volume_gb
  type              = "gp3"
  encrypted         = true
  tags              = { Name = "${var.name_prefix}-neo4j-data" }
}

data "aws_subnet" "first" {
  id = var.private_subnet_ids[0]
}

resource "aws_instance" "neo4j" {
  ami                    = var.neo4j_ami_id == "" ? data.aws_ami.al2023.id : var.neo4j_ami_id
  instance_type          = var.neo4j_instance_type
  subnet_id              = var.private_subnet_ids[0]
  vpc_security_group_ids = [aws_security_group.neo4j.id]
  iam_instance_profile   = aws_iam_instance_profile.neo4j.name

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = <<-EOT
    #!/usr/bin/env bash
    set -Eeuo pipefail
    dnf -y update
    dnf -y install docker awscli
    systemctl enable --now docker

    # Wait for the data volume to attach, then mount it
    DEV=/dev/xvdf
    for i in $(seq 1 30); do [ -b "$DEV" ] && break; sleep 2; done
    if ! blkid "$DEV" >/dev/null; then mkfs.xfs "$DEV"; fi
    mkdir -p /var/lib/neo4j-data
    grep -q "$DEV" /etc/fstab || echo "$DEV /var/lib/neo4j-data xfs defaults,nofail 0 2" >> /etc/fstab
    mount -a

    NEO4J_PASSWORD=$(aws ssm get-parameter \
      --region ${var.aws_region} \
      --name /${var.name_prefix}/NEO4J_PASSWORD \
      --with-decryption --query Parameter.Value --output text)

    docker rm -f neo4j 2>/dev/null || true
    docker run -d --restart unless-stopped --name neo4j \
      -p 7474:7474 -p 7687:7687 \
      -e NEO4J_AUTH="neo4j/$NEO4J_PASSWORD" \
      -e NEO4J_PLUGINS='["apoc","graph-data-science"]' \
      -e NEO4J_dbms_security_procedures_unrestricted='apoc.*,gds.*' \
      -e NEO4J_dbms_security_procedures_allowlist='apoc.*,gds.*' \
      -e NEO4J_server_memory_pagecache_size=512M \
      -e NEO4J_server_memory_heap_initial__size=512m \
      -e NEO4J_server_memory_heap_max__size=2G \
      -v /var/lib/neo4j-data:/data \
      neo4j:5.26.9-community-bullseye
  EOT

  tags = { Name = "${var.name_prefix}-neo4j" }

  lifecycle {
    ignore_changes = [ami]  # don't replace just because the AL2023 AMI moved
  }
}

resource "aws_volume_attachment" "neo4j_data" {
  device_name = "/dev/xvdf"
  volume_id   = aws_ebs_volume.neo4j_data.id
  instance_id = aws_instance.neo4j.id
}
