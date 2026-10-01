"""
Step-by-step guide for hosting the Eugene platform on AWS, with S3 as the
static-frontend tier and ECS Fargate / EC2 for the backend services.
"""

DOC_TITLE    = "Eugene Platform — AWS Hosting Guide"
DOC_SUBTITLE = ("End-to-end deployment runbook: S3 + CloudFront for the "
                "static frontend, ECS Fargate for services, EC2 for Neo4j")
DOC_FILE_PDF  = "EUGENE_AWS_HOSTING_GUIDE.pdf"
DOC_FILE_DOCX = "EUGENE_AWS_HOSTING_GUIDE.docx"


BOOK = [

    # ════════════════════════════════════════════════════════════════
    ("PART", "Front Matter"),

    ("CHAPTER", "About this Guide"),
    ("PARA",
     "This guide walks through hosting the Eugene biomedical knowledge "
     "graph and agentic AI platform on AWS. It is written as a runbook: "
     "every step is a concrete action with the exact AWS service, console "
     "navigation, and CLI commands required."),

    ("CALLOUT",
     "Important — Amazon S3 alone is a static-object store. It can host "
     "the compiled Next.js UI (HTML / JS / CSS / images), but it cannot "
     "run the Eugene backend services (FastAPI Core API, MCP Server, "
     "Strands Agent, Streamlit UI, Neo4j). This guide therefore uses S3 "
     "for the static frontend and ECS Fargate + EC2 for the backend. If "
     "you literally need only an S3 deployment, you can host the docs "
     "and the Next.js UI on S3 and point it at an existing Eugene "
     "backend running elsewhere."),

    ("CHAPTER", "Target Architecture (Summary)"),
    ("PARA",
     "The deployment splits the stack across the following AWS services:"),
    ("TABLE", [
        ["Tier",                       "AWS Service",                          "Why"],
        ["Static frontend",            "S3 + CloudFront + Route 53 + ACM",     "Cheap, global, cached; perfect for a Next.js static export"],
        ["Agent + Core API + MCP",     "ECS Fargate",                          "Containerised Python services, auto-scale, no servers to patch"],
        ["Streamlit UI (optional)",    "ECS Fargate",                          "Streamlit is a Python server — cannot live on S3"],
        ["Knowledge graph (Neo4j)",    "EC2 (or Amazon Neptune)",               "Neo4j needs persistent storage + tuning"],
        ["Load balancing",             "Application Load Balancer",             "TLS termination + path-based routing"],
        ["Container registry",         "ECR",                                  "Stores agent / core / mcp / ui images"],
        ["Secrets",                    "AWS Secrets Manager + KMS",            "Tokens, DB credentials, OpenAI / Anthropic keys"],
        ["Observability",              "CloudWatch + X-Ray",                   "Logs, metrics, distributed tracing"],
        ["Identity",                   "Microsoft Entra ID + Cognito (federated)", "Existing CSL SSO"],
        ["CI / CD",                    "CodePipeline + CodeBuild + CodeDeploy", "Automated image build + ECS rolling deploy"],
    ]),


    # ════════════════════════════════════════════════════════════════
    ("PART", "Section 1 — Prerequisites"),

    ("CHAPTER", "1.  Local Workstation Setup"),
    ("BULLETS", [
        "AWS account with admin access (or scoped role allowing IAM, S3, EC2, ECS, ECR, ALB, CloudFront, ACM, Route53, Secrets Manager, KMS, CloudWatch).",
        "AWS CLI v2 installed and configured (`aws configure` with an Access Key + region — e.g. eu-central-1 or us-east-1).",
        "Docker Desktop ≥ 4.30 running locally.",
        "Node.js 20 LTS + npm 10 for building the Next.js frontend.",
        "Terraform ≥ 1.7 OR AWS CDK 2.x if you prefer programmatic IaC. CloudFormation works too.",
        "A domain name you control (e.g. eugene.csl.example) for the public frontend. Route 53-managed is easiest.",
        "Microsoft Entra ID tenant + an App Registration (same as the current Eugene OAuth setup).",
        "An OpenAI or Anthropic API key (used by the agent for LLM inference).",
    ]),

    ("CHAPTER", "2.  Pre-flight Checks"),
    ("CODE",
     "# 1. Confirm AWS identity\n"
     "aws sts get-caller-identity\n\n"
     "# 2. Confirm region\n"
     "aws configure get region\n\n"
     "# 3. Confirm Docker is running\n"
     "docker info | head -5\n\n"
     "# 4. Confirm Node + npm versions\n"
     "node --version    # v20.x\n"
     "npm --version     # 10.x"),


    # ════════════════════════════════════════════════════════════════
    ("PART", "Section 2 — Networking Foundation"),

    ("CHAPTER", "3.  Create a VPC (One-Time)"),
    ("PARA",
     "Eugene needs a private VPC with both public subnets (for the ALB) "
     "and private subnets (for ECS tasks and Neo4j). Use AWS-managed "
     "VPC creation for sane defaults."),
    ("NUMBERED", [
        "Console → VPC → Create VPC → 'VPC and more'.",
        "Name tag: eugene-prod-vpc; IPv4 CIDR: 10.0.0.0/16.",
        "Availability zones: 2 (e.g. eu-central-1a, eu-central-1b).",
        "Public subnets: 2 (one per AZ); private subnets: 2 (one per AZ).",
        "NAT gateway: 1 per AZ (or 1 to save cost — accept the SPOF in dev).",
        "VPC endpoints: enable S3 Gateway endpoint (free).",
        "Click 'Create VPC'. Note the VPC ID, subnet IDs, and route-table IDs that come out."
    ]),

    ("CHAPTER", "4.  Security Groups"),
    ("PARA", "Create three security groups via Console → EC2 → Security Groups:"),
    ("TABLE", [
        ["Name",                    "Inbound rules"],
        ["eugene-alb-sg",           "443 from 0.0.0.0/0 (HTTPS); 80 from 0.0.0.0/0 (HTTP redirect)"],
        ["eugene-ecs-sg",           "8000-8501 from eugene-alb-sg only"],
        ["eugene-neo4j-sg",         "7687 from eugene-ecs-sg only; 7474 from your bastion IP only"],
    ]),


    # ════════════════════════════════════════════════════════════════
    ("PART", "Section 3 — Static Frontend on S3 + CloudFront"),

    ("CHAPTER", "5.  Build the Next.js UI for Static Export"),
    ("PARA",
     "The Next.js v2 UI ships with server-side features (API routes, SSR). "
     "For S3 hosting, configure static export so it produces pure HTML, "
     "CSS, and JS. Server-only API routes will be retired (the agent and "
     "core API live on ECS and the frontend talks to them directly)."),
    ("CODE",
     "# In agents/eugene-agent-ui-next/next.config.js, add:\n"
     "module.exports = {\n"
     "  output: 'export',\n"
     "  images: { unoptimized: true },\n"
     "  trailingSlash: true,\n"
     "  env: {\n"
     "    NEXT_PUBLIC_AGENT_API: 'https://api.eugene.csl.example/agent/api',\n"
     "    NEXT_PUBLIC_CORE_API:  'https://api.eugene.csl.example/core',\n"
     "  },\n"
     "};"),
    ("CODE",
     "cd agents/eugene-agent-ui-next\n"
     "npm install\n"
     "npm run build               # produces ./out/ directory\n"
     "ls out                      # confirm static HTML / _next / assets"),
    ("CALLOUT",
     "Streamlit cannot be statically exported — it must run as a Python "
     "server. If you need the Streamlit UI in production, deploy it as an "
     "additional ECS Fargate service (see Section 5)."),

    ("CHAPTER", "6.  Create the S3 Bucket"),
    ("CODE",
     "# Replace <region> and <bucket-name>; the bucket name must be globally unique.\n"
     "aws s3api create-bucket \\\n"
     "  --bucket eugene-frontend-prod \\\n"
     "  --region eu-central-1 \\\n"
     "  --create-bucket-configuration LocationConstraint=eu-central-1\n\n"
     "# Block public access (CloudFront will read via OAC — Origin Access Control)\n"
     "aws s3api put-public-access-block \\\n"
     "  --bucket eugene-frontend-prod \\\n"
     "  --public-access-block-configuration \\\n"
     "      BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true\n\n"
     "# Enable versioning (rollback safety) and default encryption\n"
     "aws s3api put-bucket-versioning --bucket eugene-frontend-prod \\\n"
     "  --versioning-configuration Status=Enabled\n"
     "aws s3api put-bucket-encryption --bucket eugene-frontend-prod \\\n"
     "  --server-side-encryption-configuration '{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":{\"SSEAlgorithm\":\"AES256\"}}]}'"),

    ("CHAPTER", "7.  Upload the Build"),
    ("CODE",
     "aws s3 sync agents/eugene-agent-ui-next/out/ s3://eugene-frontend-prod/ \\\n"
     "  --delete \\\n"
     "  --cache-control 'public, max-age=31536000, immutable' \\\n"
     "  --exclude '*.html' \\\n"
     "  --exclude '*.json'\n\n"
     "# Re-upload HTML / JSON with shorter cache so deployments propagate fast\n"
     "aws s3 sync agents/eugene-agent-ui-next/out/ s3://eugene-frontend-prod/ \\\n"
     "  --cache-control 'public, max-age=60, must-revalidate' \\\n"
     "  --content-type 'text/html' \\\n"
     "  --exclude '*' \\\n"
     "  --include '*.html' --include '*.json'"),

    ("CHAPTER", "8.  Request a TLS Certificate (ACM)"),
    ("PARA",
     "CloudFront requires ACM certificates in us-east-1 regardless of where "
     "the backend lives."),
    ("CODE",
     "aws acm request-certificate \\\n"
     "  --domain-name eugene.csl.example \\\n"
     "  --subject-alternative-names api.eugene.csl.example www.eugene.csl.example \\\n"
     "  --validation-method DNS \\\n"
     "  --region us-east-1"),
    ("PARA",
     "Then go to ACM → click the pending cert → 'Create records in Route 53' "
     "to auto-add the DNS validation CNAME records. Wait ~5 minutes for "
     "validation."),

    ("CHAPTER", "9.  CloudFront Distribution"),
    ("NUMBERED", [
        "Console → CloudFront → Create distribution.",
        "Origin domain: select the eugene-frontend-prod S3 bucket (NOT the website endpoint).",
        "Origin access: 'Origin access control settings' → Create OAC named eugene-frontend-oac.",
        "After distribution is created, copy the OAC bucket policy back to the S3 bucket (CloudFront shows a 'Copy policy' button).",
        "Default cache behaviour: redirect HTTP → HTTPS; allowed methods GET, HEAD; cache policy CachingOptimized.",
        "Default root object: index.html.",
        "Custom error pages: 403 → /index.html (200) and 404 → /index.html (200). This is the SPA-routing pattern that lets Next.js client-side routes work.",
        "Alternate domain names (CNAMEs): eugene.csl.example.",
        "Custom SSL certificate: pick the ACM cert created in step 8.",
        "WAF: optional but recommended — attach AWS Managed Rules core rule set.",
        "Click 'Create distribution'. Distribution domain looks like dxxxxx.cloudfront.net — note it.",
    ]),

    ("CHAPTER", "10.  Route 53 — Point Domain at CloudFront"),
    ("CODE",
     "# Console: Route 53 → Hosted zones → csl.example → Create record\n"
     "# Record name:   eugene\n"
     "# Type:          A — IPv4\n"
     "# Alias:         Yes\n"
     "# Route traffic: Alias to CloudFront distribution → dxxxxx.cloudfront.net\n"
     "# Or CLI:\n"
     "aws route53 change-resource-record-sets --hosted-zone-id Z123 --change-batch file://route53.json"),


    # ════════════════════════════════════════════════════════════════
    ("PART", "Section 4 — Backend Services on ECS Fargate"),

    ("CHAPTER", "11.  Create ECR Repositories"),
    ("CODE",
     "for svc in eugene_ws eugene_mcp eugene_agent_ws eugene_agent_ui; do\n"
     "  aws ecr create-repository --repository-name eugene/${svc} --region eu-central-1 \\\n"
     "    --image-scanning-configuration scanOnPush=true \\\n"
     "    --encryption-configuration encryptionType=KMS\n"
     "done"),

    ("CHAPTER", "12.  Build & Push Images"),
    ("CODE",
     "ACCT=$(aws sts get-caller-identity --query Account --output text)\n"
     "REGION=eu-central-1\n"
     "REGISTRY=${ACCT}.dkr.ecr.${REGION}.amazonaws.com\n\n"
     "aws ecr get-login-password --region ${REGION} | \\\n"
     "  docker login --username AWS --password-stdin ${REGISTRY}\n\n"
     "# Build (the project already has these Dockerfiles)\n"
     "for svc in eugene_ws eugene_mcp eugene_agent_ws eugene_agent_ui; do\n"
     "  docker build -f docker/${svc}/Dockerfile -t ${REGISTRY}/eugene/${svc}:v1.0 . \\\n"
     "    --platform linux/amd64\n"
     "  docker push ${REGISTRY}/eugene/${svc}:v1.0\n"
     "done"),

    ("CHAPTER", "13.  Create the ECS Cluster"),
    ("CODE",
     "aws ecs create-cluster --cluster-name eugene-prod \\\n"
     "  --capacity-providers FARGATE FARGATE_SPOT \\\n"
     "  --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1"),

    ("CHAPTER", "14.  Task Definitions"),
    ("PARA",
     "Each service needs its own task definition. Save the following JSON "
     "to a file (e.g. eugene-ws.task-def.json), then register:"),
    ("CODE",
     "aws ecs register-task-definition --cli-input-json file://eugene-ws.task-def.json\n"
     "# Repeat for eugene-mcp, eugene-agent-ws, eugene-agent-ui"),
    ("CODE",
     "// eugene-ws.task-def.json — example\n"
     "{\n"
     "  \"family\": \"eugene-ws\",\n"
     "  \"networkMode\": \"awsvpc\",\n"
     "  \"requiresCompatibilities\": [\"FARGATE\"],\n"
     "  \"cpu\": \"1024\",   \"memory\": \"2048\",\n"
     "  \"executionRoleArn\": \"arn:aws:iam::ACCT:role/ecsTaskExecutionRole\",\n"
     "  \"taskRoleArn\":      \"arn:aws:iam::ACCT:role/eugene-task-role\",\n"
     "  \"containerDefinitions\": [{\n"
     "    \"name\":  \"eugene-ws\",\n"
     "    \"image\": \"ACCT.dkr.ecr.eu-central-1.amazonaws.com/eugene/eugene_ws:v1.0\",\n"
     "    \"portMappings\": [{ \"containerPort\": 8000 }],\n"
     "    \"essential\": true,\n"
     "    \"secrets\": [\n"
     "      {\"name\":\"NEO4J_PASSWORD\",       \"valueFrom\":\"arn:aws:secretsmanager:eu-central-1:ACCT:secret:eugene/neo4j-password\"},\n"
     "      {\"name\":\"EUGENE_CLIENT_SECRET\", \"valueFrom\":\"arn:aws:secretsmanager:eu-central-1:ACCT:secret:eugene/jwt-secret\"}\n"
     "    ],\n"
     "    \"environment\": [\n"
     "      {\"name\":\"NEO4J_URI\",      \"value\":\"bolt://eugene-neo4j.prod.local:7687\"},\n"
     "      {\"name\":\"NEO4J_USERNAME\", \"value\":\"neo4j\"},\n"
     "      {\"name\":\"ENVIRONMENT\",    \"value\":\"production\"}\n"
     "    ],\n"
     "    \"logConfiguration\": {\n"
     "      \"logDriver\": \"awslogs\",\n"
     "      \"options\": {\n"
     "        \"awslogs-group\": \"/ecs/eugene-ws\",\n"
     "        \"awslogs-region\": \"eu-central-1\",\n"
     "        \"awslogs-stream-prefix\": \"ws\"\n"
     "      }\n"
     "    },\n"
     "    \"healthCheck\": {\n"
     "      \"command\": [\"CMD-SHELL\",\"curl -f http://localhost:8000/health || exit 1\"],\n"
     "      \"interval\": 30, \"timeout\": 5, \"retries\": 3, \"startPeriod\": 30\n"
     "    }\n"
     "  }]\n"
     "}"),

    ("CHAPTER", "15.  Application Load Balancer + Target Groups"),
    ("NUMBERED", [
        "Console → EC2 → Load Balancers → Create → Application Load Balancer.",
        "Name: eugene-alb-prod; Scheme: internet-facing (or internal if behind corporate VPN).",
        "VPC: eugene-prod-vpc; Mappings: 2 public subnets; Security group: eugene-alb-sg.",
        "Listeners: HTTPS:443 (attach ACM cert from step 8); HTTP:80 → redirect to 443.",
        "Create target groups (Type=IP, Port=8000/8001/8443/8501): eugene-ws-tg, eugene-mcp-tg, eugene-agent-tg, eugene-streamlit-tg.",
        "Health-check path for each: /health.",
        "On the HTTPS:443 listener, add path-based rules: /core/* → eugene-ws-tg; /agent/api/* → eugene-agent-tg; /mcp/* → eugene-mcp-tg; /streamlit/* → eugene-streamlit-tg; default → return-403.",
    ]),

    ("CHAPTER", "16.  ECS Services"),
    ("CODE",
     "for svc in eugene-ws eugene-mcp eugene-agent-ws eugene-agent-ui; do\n"
     "  aws ecs create-service \\\n"
     "    --cluster eugene-prod \\\n"
     "    --service-name ${svc} \\\n"
     "    --task-definition ${svc} \\\n"
     "    --desired-count 2 \\\n"
     "    --launch-type FARGATE \\\n"
     "    --network-configuration 'awsvpcConfiguration={subnets=[subnet-priv1,subnet-priv2],securityGroups=[sg-ecs],assignPublicIp=DISABLED}' \\\n"
     "    --load-balancers \"targetGroupArn=arn:aws:elasticloadbalancing:...:targetgroup/${svc}-tg,containerName=${svc},containerPort=8000\" \\\n"
     "    --deployment-configuration 'maximumPercent=200,minimumHealthyPercent=100' \\\n"
     "    --health-check-grace-period-seconds 60\ndone"),


    # ════════════════════════════════════════════════════════════════
    ("PART", "Section 5 — Neo4j Knowledge Graph"),

    ("CHAPTER", "17.  Launch a Neo4j EC2 Instance"),
    ("PARA",
     "Two viable options. The simpler one is to run Neo4j Enterprise on a "
     "dedicated EC2 instance with EBS storage. The fully-managed alternative "
     "is Amazon Neptune (Cypher-compatible), but it requires schema "
     "translation work first — start with Neo4j on EC2."),
    ("NUMBERED", [
        "Console → EC2 → Launch instance.",
        "Name: eugene-neo4j-prod.",
        "AMI: Amazon Linux 2023 (or Ubuntu 24.04 LTS).",
        "Instance type: r6i.2xlarge for production (8 vCPU, 64 GB RAM). r6i.xlarge for staging.",
        "Network: eugene-prod-vpc, private subnet, security group eugene-neo4j-sg.",
        "Storage: 200 GB gp3 EBS, encrypted with the eugene-data-cmk KMS key.",
        "User data: install Neo4j 5.x community or enterprise (see commands below).",
        "IAM role: attach an instance profile granting CloudWatch Agent + Systems Manager access.",
    ]),
    ("CODE",
     "# Neo4j install user-data (Amazon Linux 2023)\n"
     "#!/bin/bash\n"
     "yum update -y\n"
     "yum install -y java-17-amazon-corretto\n"
     "rpm --import https://debian.neo4j.com/neotechnology.gpg.key\n"
     "cat > /etc/yum.repos.d/neo4j.repo <<EOF\n"
     "[neo4j]\n"
     "name=Neo4j RPM Repository\n"
     "baseurl=https://yum.neo4j.com/stable/5\n"
     "enabled=1\ngpgcheck=1\nEOF\n"
     "yum install -y neo4j-5.26.0\n"
     "echo 'server.default_listen_address=0.0.0.0' >> /etc/neo4j/neo4j.conf\n"
     "echo 'server.memory.pagecache.size=20G'   >> /etc/neo4j/neo4j.conf\n"
     "echo 'server.memory.heap.initial_size=8G' >> /etc/neo4j/neo4j.conf\n"
     "echo 'server.memory.heap.max_size=8G'     >> /etc/neo4j/neo4j.conf\n"
     "neo4j-admin dbms set-initial-password \"$(aws secretsmanager get-secret-value --secret-id eugene/neo4j-password --query SecretString --output text)\"\n"
     "systemctl enable neo4j && systemctl start neo4j"),

    ("CHAPTER", "18.  Internal DNS for Neo4j"),
    ("CODE",
     "# Use Route 53 private hosted zone (created with the VPC)\n"
     "# Add an A record for eugene-neo4j.prod.local → the EC2 private IP\n"
     "aws route53 change-resource-record-sets \\\n"
     "  --hosted-zone-id ZONE_ID \\\n"
     "  --change-batch '{\n"
     "    \"Changes\":[{\"Action\":\"CREATE\",\"ResourceRecordSet\":{\n"
     "      \"Name\":\"eugene-neo4j.prod.local\",\"Type\":\"A\",\"TTL\":60,\n"
     "      \"ResourceRecords\":[{\"Value\":\"10.0.20.42\"}]}}]}'"),

    ("CHAPTER", "19.  Seed Initial Data"),
    ("PARA", "From a developer workstation (over Session Manager or VPN):"),
    ("CODE",
     "# Open Session Manager port-forward\n"
     "aws ssm start-session --target i-0abc123 \\\n"
     "  --document-name AWS-StartPortForwardingSession \\\n"
     "  --parameters portNumber=7687,localPortNumber=7687\n\n"
     "# In another terminal: pump the seed scripts in\n"
     "for f in bin/seed/csl_behring_assets.cypher \\\n"
     "         bin/seed/biogen_assets.cypher \\\n"
     "         bin/seed/biogen_assets_patch_labels.cypher \\\n"
     "         bin/seed/csl_drug_node_properties.cypher; do\n"
     "  cat \"$f\" | cypher-shell -a bolt://localhost:7687 -u neo4j \\\n"
     "    -p \"$(aws secretsmanager get-secret-value --secret-id eugene/neo4j-password --query SecretString --output text)\"\ndone"),


    # ════════════════════════════════════════════════════════════════
    ("PART", "Section 6 — Secrets, IAM, and Observability"),

    ("CHAPTER", "20.  Secrets Manager"),
    ("CODE",
     "aws secretsmanager create-secret --name eugene/neo4j-password \\\n"
     "  --secret-string 'CHANGE_ME_STRONG_PASSWORD' \\\n"
     "  --kms-key-id alias/eugene-data-cmk\n\n"
     "aws secretsmanager create-secret --name eugene/jwt-secret \\\n"
     "  --secret-string \"$(openssl rand -hex 48)\"\n\n"
     "aws secretsmanager create-secret --name eugene/openai-key \\\n"
     "  --secret-string 'sk-proj-...'\n\n"
     "aws secretsmanager create-secret --name eugene/entra-client-secret \\\n"
     "  --secret-string '...'"),

    ("CHAPTER", "21.  IAM Roles"),
    ("PARA",
     "Two roles are needed: ecsTaskExecutionRole (pulls images, writes "
     "logs) and eugene-task-role (the task's own runtime role for "
     "Secrets Manager + KMS access)."),
    ("CODE",
     "# ecsTaskExecutionRole — managed policy + ECR secrets read\n"
     "aws iam create-role --role-name ecsTaskExecutionRole \\\n"
     "  --assume-role-policy-document file://ecs-trust.json\n"
     "aws iam attach-role-policy --role-name ecsTaskExecutionRole \\\n"
     "  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy\n\n"
     "# eugene-task-role — fine-grained read for Eugene's secrets\n"
     "aws iam create-role --role-name eugene-task-role \\\n"
     "  --assume-role-policy-document file://ecs-trust.json\n"
     "aws iam put-role-policy --role-name eugene-task-role \\\n"
     "  --policy-name eugene-secrets-read \\\n"
     "  --policy-document file://eugene-secrets-policy.json"),

    ("CHAPTER", "22.  CloudWatch Logs + Metrics"),
    ("CODE",
     "for svc in eugene-ws eugene-mcp eugene-agent-ws eugene-agent-ui; do\n"
     "  aws logs create-log-group --log-group-name /ecs/${svc} --region eu-central-1\n"
     "  aws logs put-retention-policy --log-group-name /ecs/${svc} --retention-in-days 30\ndone\n\n"
     "# Container Insights for cluster-level metrics\n"
     "aws ecs put-account-setting --name containerInsights --value enabled"),


    # ════════════════════════════════════════════════════════════════
    ("PART", "Section 7 — CI / CD"),

    ("CHAPTER", "23.  GitHub Actions → ECR"),
    ("CODE",
     "# .github/workflows/deploy.yml (excerpt)\n"
     "name: deploy\n"
     "on:\n"
     "  push:\n"
     "    branches: [main]\n"
     "permissions:\n"
     "  id-token: write\n"
     "  contents: read\n"
     "jobs:\n"
     "  build-and-push:\n"
     "    runs-on: ubuntu-latest\n"
     "    steps:\n"
     "      - uses: actions/checkout@v4\n"
     "      - uses: aws-actions/configure-aws-credentials@v4\n"
     "        with:\n"
     "          role-to-assume: arn:aws:iam::ACCT:role/eugene-github-deploy\n"
     "          aws-region: eu-central-1\n"
     "      - uses: aws-actions/amazon-ecr-login@v2\n"
     "      - run: ./bin/docker/ecr/build.sh\n"
     "      - run: ./bin/docker/ecr/push.sh\n"
     "      - run: aws ecs update-service --cluster eugene-prod \\\n"
     "                --service eugene-ws --force-new-deployment"),

    ("CHAPTER", "24.  Frontend Sync on Every Release"),
    ("CODE",
     "# Append to the deploy workflow above\n"
     "  deploy-frontend:\n"
     "    needs: build-and-push\n"
     "    runs-on: ubuntu-latest\n"
     "    steps:\n"
     "      - uses: actions/checkout@v4\n"
     "      - uses: actions/setup-node@v4\n"
     "        with: { node-version: '20' }\n"
     "      - run: cd agents/eugene-agent-ui-next && npm ci && npm run build\n"
     "      - uses: aws-actions/configure-aws-credentials@v4\n"
     "        with:\n"
     "          role-to-assume: arn:aws:iam::ACCT:role/eugene-github-deploy\n"
     "          aws-region: eu-central-1\n"
     "      - run: aws s3 sync agents/eugene-agent-ui-next/out/ s3://eugene-frontend-prod/ --delete\n"
     "      - run: aws cloudfront create-invalidation \\\n"
     "                --distribution-id E1ABC --paths '/*'"),


    # ════════════════════════════════════════════════════════════════
    ("PART", "Section 8 — Smoke Tests & Cutover"),

    ("CHAPTER", "25.  End-to-End Smoke Test"),
    ("CODE",
     "# 1. Public frontend\n"
     "curl -sI https://eugene.csl.example/ | head -3\n\n"
     "# 2. ALB health\n"
     "curl -sS https://api.eugene.csl.example/core/health\n"
     "curl -sS https://api.eugene.csl.example/agent/api/health\n\n"
     "# 3. Obtain JWT (Entra federated or local-bypass)\n"
     "TOKEN=$(curl -sS https://api.eugene.csl.example/core/login | grep -oE 'eyJ[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+' | head -1)\n\n"
     "# 4. Hit a graph endpoint\n"
     "curl -sS -H \"Authorization: Bearer $TOKEN\" \\\n"
     "  https://api.eugene.csl.example/core/node/find/Hemophilia | head -200\n\n"
     "# 5. Agent end-to-end\n"
     "curl -sS -N -X POST https://api.eugene.csl.example/agent/api/query/stream \\\n"
     "  -H \"Authorization: Bearer $TOKEN\" \\\n"
     "  -H 'Content-Type: application/json' \\\n"
     "  -d '{\"prompt\":\"What is Andembry?\",\"conversation_id\":\"00000000-0000-0000-0000-000000000001\"}' | head -10"),

    ("CHAPTER", "26.  Rollback Plan"),
    ("BULLETS", [
        "S3 versioning: aws s3api list-object-versions then aws s3api copy-object with --version-id.",
        "CloudFront cache flush: aws cloudfront create-invalidation --paths '/*'.",
        "ECS: each service tracks the previous task definition revision; `aws ecs update-service --task-definition <previous-rev>` rolls back instantly.",
        "Neo4j: take an automated snapshot of the EBS volume nightly; restore by creating a new EBS volume from the snapshot and remounting.",
    ]),


    # ════════════════════════════════════════════════════════════════
    ("PART", "Section 9 — Operations"),

    ("CHAPTER", "27.  Cost Outlook (us-east-1, monthly)"),
    ("TABLE", [
        ["Service",                "Sizing",                                      "Approx. USD / month"],
        ["S3 + CloudFront",         "10 GB static + 200 GB egress",                "$20"],
        ["ALB",                     "Always-on, 2 AZ",                             "$25"],
        ["ECS Fargate (4 services × 2 tasks)", "1 vCPU / 2 GB each", "$220"],
        ["EC2 r6i.2xlarge (Neo4j)", "1 instance, 24/7",                             "$390"],
        ["EBS gp3 200 GB",          "Neo4j data",                                  "$18"],
        ["Secrets Manager",         "4 secrets",                                   "$2"],
        ["CloudWatch Logs",          "30-day retention, ~10 GB/mo",                 "$10"],
        ["NAT Gateway",             "1 AZ",                                        "$35"],
        ["Route 53 hosted zone",    "1 zone",                                      "$0.50"],
        ["ACM",                     "Public cert",                                 "Free"],
        ["**Total**",               "**Single-AZ baseline**",                       "**≈ $720**"],
    ]),

    ("CHAPTER", "28.  Monitoring + Alerts"),
    ("BULLETS", [
        "CloudWatch alarms: ALB 5xx > 1% over 5 minutes; ECS service CPU > 80%; Neo4j EC2 disk > 80%.",
        "Synthetics canary: every 5 minutes, GET https://eugene.csl.example/ and hit /core/health.",
        "Log Insights queries (saved): error pattern by service, slow query > 2s, JWT validation failures.",
        "Service map via AWS X-Ray once OpenTelemetry is wired into eugene-agent-ws (see the Technical Recommendations doc).",
    ]),

    ("CHAPTER", "29.  Security Hardening Checklist"),
    ("NUMBERED", [
        "Enable AWS WAF on the CloudFront distribution with AWS Managed Rules: Core, Known Bad Inputs, SQL DB.",
        "Turn on GuardDuty + Security Hub at the account level.",
        "Force MFA on the AWS root account; create IAM users only via Identity Center.",
        "Bedrock Guardrails on every LLM call (when migrating to Bedrock).",
        "AWS Macie scan on S3 buckets (for sensitive-data classification).",
        "Daily AWS Config rule scans against CIS benchmark.",
        "AWS Backup with cross-region copy for Neo4j EBS volume and Secrets Manager.",
        "Rotate KMS CMK every 90 days; rotate Secrets Manager values via Lambda hook.",
    ]),


    # ════════════════════════════════════════════════════════════════
    ("PART", "Appendices"),

    ("CHAPTER", "Appendix A — Terraform Module Layout"),
    ("PARA",
     "Recommended directory layout if you choose Terraform over manual "
     "console steps:"),
    ("CODE",
     "infrastructure/\n"
     "├── envs/\n"
     "│   ├── prod/\n"
     "│   │   ├── backend.tf       # remote-state S3 + DynamoDB lock\n"
     "│   │   ├── main.tf          # composes all modules\n"
     "│   │   └── terraform.tfvars # prod-specific values\n"
     "│   └── staging/\n"
     "└── modules/\n"
     "    ├── vpc/\n"
     "    ├── alb/\n"
     "    ├── ecr/\n"
     "    ├── ecs-service/\n"
     "    ├── ec2-neo4j/\n"
     "    ├── s3-cloudfront-spa/\n"
     "    ├── secrets/\n"
     "    └── monitoring/"),

    ("CHAPTER", "Appendix B — Troubleshooting"),
    ("TABLE", [
        ["Symptom",                                       "Likely cause / fix"],
        ["403 from CloudFront",                            "OAC bucket policy not applied — copy from CloudFront console"],
        ["S3 sync exits 'AccessDenied'",                   "User missing s3:PutObject on the bucket"],
        ["ECS task stuck in PROVISIONING",                 "Subnet has no NAT / no route to ECR — fix VPC routing"],
        ["ECS task exits with 'ResourceInitializationError'", "Task role missing secretsmanager:GetSecretValue"],
        ["ALB returns 504",                                "Target health check failing; verify /health endpoint reachable on container port"],
        ["Agent returns 'cannot connect to Neo4j'",         "Check Route 53 private record + eugene-neo4j-sg ingress from ECS sg"],
        ["CloudFront SSL handshake fails",                  "ACM cert is in wrong region (must be us-east-1) or domain mismatch"],
        ["Frontend 404s on deep links",                    "Add 403/404 → /index.html (200) custom error pages on CloudFront"],
    ]),

    ("CHAPTER", "Appendix C — Useful CLI One-Liners"),
    ("CODE",
     "# Force redeploy of an ECS service\n"
     "aws ecs update-service --cluster eugene-prod --service eugene-ws --force-new-deployment\n\n"
     "# Tail logs of a service\n"
     "aws logs tail /ecs/eugene-ws --follow --since 10m\n\n"
     "# Invalidate CloudFront after a frontend deploy\n"
     "aws cloudfront create-invalidation --distribution-id E1ABC --paths '/*'\n\n"
     "# Get the public CloudFront domain\n"
     "aws cloudfront list-distributions --query 'DistributionList.Items[?Aliases.Items && contains(Aliases.Items, `eugene.csl.example`)].DomainName' --output text\n\n"
     "# Open Session Manager into the Neo4j box\n"
     "aws ssm start-session --target i-0abc123\n\n"
     "# Scale an ECS service\n"
     "aws ecs update-service --cluster eugene-prod --service eugene-agent-ws --desired-count 4"),
]
