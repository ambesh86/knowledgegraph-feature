# Eugene — fresh AWS deployment (Terraform)

Stands up an isolated copy of Eugene on AWS — an ALB, ECS Fargate services
for all 5 containers, Neo4j on a single EC2, and SSM-backed secrets — under
a configurable `name_prefix` so **nothing collides with the existing
`eugene-search-*` deployment**.

## What gets created

| Resource | Count | Notes |
|---|---|---|
| ALB | 1 | internal by default, HTTPS if `alb_certificate_arn` is set |
| Target groups + listener rules | 5 | one per service, routed by path |
| ECS Fargate cluster | 1 | Container Insights enabled |
| ECS task defs + services | 5 | `eugene_ws`, `eugene_mcp`, `eugene_agent_ws`, `eugene_agent_ui`, `eugene_agent_ui_next` |
| CloudWatch log groups | 5 | 14-day retention |
| EC2 (Neo4j) | 1 | AL2023, user-data installs Docker + Neo4j 5.26 |
| EBS volume (Neo4j data) | 1 | gp3, encrypted, 100 GB default |
| Security groups | 3 | ALB / ECS / Neo4j |
| Service-discovery namespace | 1 | `<name_prefix>.local` |
| SSM SecureString parameters | 3–4 | OpenAI key, Anthropic key (optional), Eugene secret, Neo4j password |
| IAM roles | 3 | task execution, task, Neo4j EC2 |

## Pre-flight

1. **Build & publish images** via [`.github/workflows/build-images.yml`](../../../.github/workflows/build-images.yml). Confirm they're at e.g. `ghcr.io/aisemanticexpert/eugene-ws:latest`.
2. **Identify VPC + subnets** to use. Two private subnets in different AZs are required.
3. **(Optional but recommended)** Request an ACM certificate for your hostname so you get HTTPS instead of HTTP.

## Deploy

```bash
cd infrastructure/environments/fresh-deploy
cp terraform.tfvars.example terraform.tfvars
$EDITOR terraform.tfvars        # fill in vpc_id, subnets, secrets

# Optional: remote state. Otherwise Terraform stores state locally.
# cp backend.tf.example backend.tf && $EDITOR backend.tf

terraform init
terraform plan -out tfplan
terraform apply tfplan
```

Apply takes ~10 minutes (ECS rollouts dominate). The outputs include the ALB
DNS name and per-service URLs.

## Destroy

```bash
terraform destroy
```

Wipes everything in this stack. **Does not touch** the existing `eugene-search-*`
resources because all names are scoped by `var.name_prefix`.

## What this stack does NOT do (left for you)

- **DNS**: doesn't create a Route 53 record. After apply, point a CNAME at the
  ALB DNS, or use Route 53 alias from `outputs.alb_zone_id` / `alb_dns_name`.
- **WAF**: no WAFv2 association. Bolt one on if you put this on the internet.
- **Bastion**: doesn't create a jump host for Neo4j. Reach it via SSM Session
  Manager (the EC2 has the SSM agent + role).
- **Backup**: no AWS Backup plan for the Neo4j EBS volume. Add one if data matters.
- **Autoscaling**: ECS service counts are static. Add `aws_appautoscaling_*`
  resources if you need elasticity.
- **CSL central listener pattern**: prod CSL setup has the cloud team provision
  the listener separately. To mimic, set `alb_certificate_arn = ""`, then delete
  `aws_lb_listener.http` from `alb.tf` and ask cloud-team to point a listener
  at the target groups.

## Cost estimate (us-east-1, very rough)

| Item | Monthly $ |
|---|---|
| 5 Fargate tasks (0.5–1 vCPU, 1–2 GB, 24/7) | ~$80 |
| 1× t3.large EC2 + 100 GB gp3 | ~$70 |
| 1× internal ALB | ~$18 |
| NAT egress (if private subnets) | varies |
| CloudWatch logs (14 d retention, modest volume) | <$5 |
| **Total**, ignoring NAT and bandwidth | **~$175/month** |

NAT and inter-AZ data transfer are usually the surprise items. Keep all 5
services in the same AZ for dev to avoid that.

## Troubleshooting

```bash
# Tail logs
aws logs tail /ecs/eugene-fresh/eugene_agent_ws --follow --region us-east-1

# SSM into the Neo4j EC2
aws ssm start-session --target <i-instance-id> --region us-east-1

# Check task health
aws ecs describe-services \
  --cluster eugene-fresh-cluster \
  --services eugene-fresh-eugene_agent_ws \
  --region us-east-1
```
