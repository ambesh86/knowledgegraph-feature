# Eugene UI-only EC2 deploy

Single EC2 in your VPC running the prebuilt `eugene-agent-ui-next` Docker
image as a systemd service. The UI talks to the existing internal ALB
(`internal-eugene-search-alb-...elb.amazonaws.com`) for all backend calls.

## Prerequisites

1. The `eugene-agent-ui-next` image is published. The CI workflow
   [`.github/workflows/build-images.yml`](../../../.github/workflows/build-images.yml)
   pushes it to `ghcr.io/aisemanticexpert/eugene-agent-ui-next:latest`.
2. You have an AWS VPC + subnet ID. The subnet must:
   - be in the **same VPC** as the internal Eugene ALB (so the UI can call it),
   - be a **public** subnet if you want browser access from the internet, or
     reachable via your corporate VPN if private.
3. AWS CLI configured with permission to create EC2/IAM/SG/SSM resources.

## Deploy

```bash
cd infrastructure/environments/ui-only-ec2
cp terraform.tfvars.example terraform.tfvars
$EDITOR terraform.tfvars       # set vpc_id, subnet_id, allow_ingress_cidrs

terraform init
terraform plan -out tfplan     # REVIEW
terraform apply tfplan
```

When apply finishes (~3 min), `terraform output` shows:

```
ui_url_public  = "http://<EIP>/"          # browser URL
ui_url_private = "http://10.x.x.x/"       # VPC-internal URL
ssm_start_session_cmd = "aws ssm start-session --target i-... --region us-east-1"
tail_bootstrap_log_cmd = "aws ssm ... tail -f /var/log/eugene-ui-bootstrap.log"
```

Wait an extra 1–2 minutes after apply for user-data to finish pulling and
starting the container. Tail the bootstrap log to see progress.

## What the EC2 does on first boot

The user-data script (in [ec2.tf](ec2.tf)) does this:

1. `dnf -y update && dnf -y install docker awscli`
2. `systemctl enable --now docker`
3. (Optional) `docker login ghcr.io` with credentials from SSM Parameter Store
4. `docker pull <ui_image>`
5. Writes `/etc/systemd/system/eugene-ui.service`
6. `systemctl enable --now eugene-ui.service`

The systemd unit runs the container with these env vars:

```
NODE_ENV=production
EUGENE_CORE_API_URL=https://internal-eugene-search-alb-616664632.../
EUGENE_AGENT_API_URL=https://internal-eugene-search-alb-616664632.../agent/api
EUGENE_MCP_SERVER_URL=https://internal-eugene-search-alb-616664632.../mcp
```

It restarts on failure and re-pulls the image on every start.

## Re-deploy a new image (no terraform run needed)

```bash
bin/redeploy_ui.sh <instance-id> <image-tag>
# e.g.
bin/redeploy_ui.sh i-0abc... sha-abc1234
```

The script uses SSM to: rewrite the systemd unit's image tag, `daemon-reload`,
restart the service, and tail the status. Takes ~30 seconds.

## Shell into the EC2

```bash
aws ssm start-session --target <instance-id> --region us-east-1
```

No SSH key needed — SSM Session Manager works through the IAM role.

## Troubleshooting

```bash
# Bootstrap log (everything user-data did)
sudo tail -f /var/log/eugene-ui-bootstrap.log

# Service status
sudo systemctl status eugene-ui

# Container logs (the UI's stdout)
sudo docker logs -f eugene-ui

# Confirm UI can reach the ALB
curl -k -I https://internal-eugene-search-alb-616664632.us-east-1.elb.amazonaws.com/health
```

If `curl` to the ALB times out from the EC2, your subnet/security group
doesn't have a route to the ALB. Confirm the EC2 is in the SAME VPC and a
subnet whose route table can reach the ALB's subnets.

## Destroy

```bash
terraform destroy
```

Removes only the resources this stack created (`eugene-ui-*`). The existing
Eugene backend stack is untouched.

## HTTPS via public ALB + ACM (optional)

Set `enable_tls = true` in `terraform.tfvars` plus:

```hcl
domain_name           = "eugene.yourcorp.com"
route53_zone_id       = "Z0123456789ABCDEFGHIJ"
alb_public_subnet_ids = ["subnet-pub-aaaaaaaa", "subnet-pub-bbbbbbbb"]
alb_public_allow_cidrs = ["203.0.113.0/24"]   # restrict!
```

What [tls.tf](tls.tf) then creates:
- `aws_acm_certificate` (DNS-validated automatically through Route 53)
- Public ALB + target group attaching the EC2 by ID
- HTTPS listener (TLS1.3) and HTTP→HTTPS 301 redirect
- Route 53 A-alias `domain_name → public ALB`
- A security-group rule so the EC2 only accepts traffic from the public ALB on the UI port

After apply, browse to `https://eugene.yourcorp.com/`. `terraform output ui_url_https` confirms.

Requirements for TLS mode:
- You own a Route 53 hosted zone that resolves `domain_name`.
- You have at least 2 public subnets (with IGW route) in different AZs in the same VPC.
- ACM cert issuance typically completes in 1–2 minutes after `apply`.

To turn it back off, set `enable_tls = false` and `apply` — Terraform deletes the cert, ALB, target group, listener rules, and DNS record. The EC2 is untouched.

## What this stack does NOT do

- **HTTP-only Let's Encrypt on the EC2 itself** — out of scope. Use the ACM/ALB path above.
- **Autoscaling** — single EC2 by design. Move to ECS Fargate if you need HA.
- **Backup** — UI is stateless; nothing to back up.
- **WAF** — bolt on `aws_wafv2_web_acl_association` to `aws_lb.public[0].arn` if you need it.
