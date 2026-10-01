# Why the app has no internet on AWS while the VDI does

**Verified against the live account on 2026-08-15** (account `087084717211`,
`us-east-1`). Everything in section 1 is a fact read from the AWS API, not an
inference. Reproduce any line with the command shown.

---

## 1. What is actually true in AWS

| Fact | Value | How to check |
|---|---|---|
| Instance | `i-0b2c86270105221ec`, private IP **10.88.204.26** | `aws ec2 describe-instances --instance-ids i-0b2c86270105221ec` |
| Subnet | `subnet-0c38f0c65b6843979` (`…-general1`, 10.88.204.0/24) | `aws ec2 describe-subnets` |
| Public IP | **none** (`associate_public_ip = false`) | as above |
| Route table | `rtb-0c77b1b81e473df17` | `aws ec2 describe-route-tables --filters Name=association.subnet-id,Values=subnet-0c38f0c65b6843979` |
| Default route | `0.0.0.0/0` → **`tgw-0122884db8995c4d1`** | as above |
| Internet gateway | **none attached to the VPC** | `aws ec2 describe-internet-gateways --filters Name=attachment.vpc-id,Values=vpc-0b055f51ee4dbec56` → empty |
| NAT gateway | **none in the VPC** | `aws ec2 describe-nat-gateways --filter Name=vpc-id,Values=vpc-0b055f51ee4dbec56` → empty |
| Security group egress | `0.0.0.0/0`, all protocols, all ports — **fully open** | `ec2.tf` line 30 |
| Network ACL | default `acl-0083ec8c7d2c5ff99` — allow all in **and** out | `aws ec2 describe-network-acls` |
| VPC endpoints | ec2, ecr.api, ecr.dkr, s3, elasticloadbalancing, codedeploy ×2, email-smtp | `aws ec2 describe-vpc-endpoints` |
| **No** endpoints for | **ssm, ssmmessages, ec2messages, secretsmanager** | as above |

### The single most important line

There is **no internet gateway and no NAT gateway anywhere in this VPC.** AWS is
not providing internet access to this instance at all, and no setting inside this
account can make it do so. Every packet for a public address is handed to the
Transit Gateway and leaves for the corporate network, where the corporate egress
stack — not AWS — decides its fate.

### The claim that the working boxes are configured differently is false

`csl-dl-admin-1`, `gitlab-runner` and `Eugene-nextgen-test` sit in
`subnet-0824e9214bbfe0336`; our UI sits in `subnet-0c38f0c65b6843979`. It is
natural to suspect the subnet move. It is not the cause:

```
both subnets → route table rtb-0c77b1b81e473df17   (identical)
both subnets → NACL acl-0083ec8c7d2c5ff99          (identical, allow-all)
```

Same route table, same NACL, same open security group. **Inside AWS the two
subnets are indistinguishable.** If one has internet and the other does not, the
difference is being made beyond the Transit Gateway, by policy keyed on the
source address — and our source address changed to `10.88.204.26` when the
instance moved out of the full `/28`.

---

## 2. So what does "we opened the port" mean?

It is almost certainly true, and almost certainly not sufficient. "Opening a
port" is one of at least four independent conditions, and the other three are
invisible from a firewall console:

| # | Condition | Who owns it | Status |
|---|---|---|---|
| 1 | A **route** to the destination | us (AWS) | ✅ present — `0.0.0.0/0` → TGW |
| 2 | A **firewall rule** permitting *this source* to *that destination* on 443 | network team | ❓ scoped to which source CIDR? |
| 3 | Traffic sent **via the proxy**, if egress is proxy-only | **us** | ❌ not configured |
| 4 | The **inspection CA trusted** by our clients, if TLS is intercepted | **us** | ❌ not installed |

Conditions 3 and 4 are ours, and they are the reason the comparison with the VDI
is misleading. **The VDI does not have plain internet access either.** It has a
browser and an OS configured with the corporate proxy (usually a PAC file) and a
machine image that already trusts the corporate inspection CA. A bare Amazon
Linux instance has neither. If corporate egress is proxy-only, our containers
will fail with connection timeouts no matter how many ports are open, because
they never send the traffic to the proxy in the first place.

That is the most likely truth here, and it is testable rather than arguable.

---

## 3. Establish which it is — one command, no debate

`bin/aws/egress-doctor.sh` tests every destination this application needs, at
each layer (DNS → TCP → TLS → HTTP), and prints what failed and what that
failure *means*. Run it on the box:

```bash
# on the instance
curl -sO https://<your-repo>/bin/aws/egress-doctor.sh   # or scp it
bash egress-doctor.sh                                   # direct egress
bash egress-doctor.sh --proxy http://<corp-proxy>:8080  # via the proxy
```

Read the result with this table — it is the whole point of running it:

| Observation | Conclusion | Owner |
|---|---|---|
| Section 2 all **timeout**, section 3 (AWS endpoints) passes | No internet egress at all; only VPC endpoints work | network team |
| Direct **timeout**, `--proxy` **passes** | Nothing is broken. Egress is proxy-only by design — configure the app | **us** |
| Some hosts pass, others **timeout** | Destination **allowlist**, not a port. Hand over the failing FQDNs | network team |
| **refused** rather than timeout | An active reject rule, wrongly scoped. Quote source `10.88.204.26` | network team |
| TLS **UNTRUSTED**, corporate issuer | Egress works and is inspected — install the CA | **us** |
| IMDS unreachable | Proxy is swallowing `169.254.169.254` — see below | **us** |

The script is verified accurate: run from a machine with real internet, every
destination passes, so a failure on the instance is a finding rather than a bug
in the test.

---

## 4. The fix, already implemented

All of this is opt-in and defaults to **off**, so `terraform apply` with no new
variables produces byte-identical user-data to today.

### If egress is proxy-only — `http_proxy_url`

```hcl
http_proxy_url   = "http://proxy.corp.example:8080"
no_proxy_extra   = ""                    # optional additions
corporate_ca_pem = file("corp-root.pem") # only if TLS is intercepted
```

This configures **three separate consumers**, none of which implies the others —
the usual reason a "we set the proxy" attempt only half-works:

1. **the Docker daemon** (`/etc/systemd/system/docker.service.d/http-proxy.conf`)
   — without it `docker pull` of the UI image fails and the box never starts;
2. **the containers** (`HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` on `docker run`);
3. **the shell and dnf** — so an operator debugging on the box sees the same path
   the app does, and `dnf update` at boot doesn't hang.

**`NO_PROXY` always contains `169.254.169.254`.** Proxying IMDS destroys the
instance role, and the symptom is "S3 access denied" — which sends people to IAM
for a day. It also excludes the ALB and Postgres, which are in-VPC and must not
take an external hop.

### If TLS is intercepted — `corporate_ca_pem`

Installed into the OS trust store *before* the first network call, and mounted
into containers with `NODE_EXTRA_CA_CERTS`, `REQUESTS_CA_BUNDLE` and
`SSL_CERT_FILE` all pointed at it. Once this works, set
`skip_alb_tls_verify = false` — that flag currently disables TLS verification
process-wide via `NODE_TLS_REJECT_UNAUTHORIZED=0`, which is a real weakness we
are carrying because the ALB cert is self-signed.

### Get a shell without internet — `enable_ssm_endpoints = true`

The VPC has no `ssm`, `ssmmessages` or `ec2messages` endpoints and no internet,
which is precisely why Session Manager does not work and why deploys are done by
rebooting the box. Three interface endpoints (~USD 22/month) fix it. Without a
shell you cannot run the diagnostic, and without the diagnostic you are
negotiating from assertion.

### Also missing — `additional_interface_endpoints = ["secretsmanager"]`

`bedrock.tf` grants the instance role `secretsmanager:GetSecretValue` for the
Eugene backend secret, but there is no Secrets Manager endpoint and no internet.
That fetch cannot currently succeed. It will look like a permissions error.

---

## 5. What to send the network team

Give them facts, not a request to "check the firewall":

> Source: **10.88.204.26** (`i-0b2c86270105221ec`, subnet `subnet-0c38f0c65b6843979`,
> 10.88.204.0/24), egressing via `tgw-0122884db8995c4d1`.
>
> Inside AWS the path is fully open — security group egress `0.0.0.0/0` all
> protocols, default NACL allow-all, default route to the TGW. There is no NAT or
> IGW, so we depend entirely on corporate egress.
>
> Please confirm, for this source address:
> 1. Is direct outbound 443 permitted, or is egress **proxy-only**? If proxy-only,
>    we need the proxy URL/PAC and whether it requires authentication — we will
>    configure the application, no firewall change needed.
> 2. Is the permit list scoped to a **source CIDR**? The host moved from
>    10.88.207.240/28 to 10.88.204.0/24; a rule written for the old range would
>    explain why comparable boxes work and this one does not.
> 3. Is the permit list scoped to **destinations**? We need these FQDNs on 443:
>    `ghcr.io`, `pkg-containers.githubusercontent.com`, `clinicaltrials.gov`,
>    `www.ebi.ac.uk`, `europepmc.org`, `eutils.ncbi.nlm.nih.gov`, `api.uspto.gov`,
>    `www.sec.gov`, and `api.openai.com` if LLM titling stays enabled.
> 4. Is TLS inspected? If so please supply the root CA — we install it, and the
>    problem is ours, not yours.

---

## 6. Known gap: Node.js does not obey `HTTP_PROXY`

Python clients (`requests`, `httpx`) read the proxy environment automatically, so
the scanner and ADE services are covered by the variables above. **Node.js 18+
`fetch` (undici) ignores `HTTP_PROXY` entirely.** If the UI must make outbound
internet calls through a proxy — today that is only OpenAI chat titling — it
needs an explicit `undici.ProxyAgent` installed via `setGlobalDispatcher` at
startup. Calls to the ALB are unaffected: they are in `NO_PROXY` and stay inside
the VPC. This is not yet implemented, and it cannot be verified without a real
proxy address to test against.
