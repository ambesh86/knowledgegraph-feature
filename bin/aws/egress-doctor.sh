#!/usr/bin/env bash
# =============================================================================
# egress-doctor — establish, layer by layer, where outbound traffic actually dies.
#
# Run this ON the EC2 instance (or inside a container on it). It answers the one
# question that "we opened the port" cannot: *which layer fails, for which
# destination, and what does the failure look like*.
#
#   DNS resolves?  →  TCP connects?  →  TLS completes?  →  HTTP responds?
#
# Each layer has a distinct signature, and the signature names the owner of the
# problem:
#
#   DNS fails ................. resolver cannot answer public names
#   TCP times out ............. no path / silently dropped (firewall DROP)
#   TCP refused (RST) ......... something answered and said no (firewall REJECT)
#   TLS fails, cert untrusted . TLS-intercepting proxy, corporate CA not installed
#   TLS fails, handshake ...... TLS inspection rejecting SNI, or protocol block
#   HTTP 403/407 .............. proxy reached, request denied / auth required
#   Works only via proxy ...... direct egress is closed by design; use the proxy
#   Some hosts work, others not  destination allowlist, not a port problem
#
# Usage:
#   ./egress-doctor.sh                      # test direct
#   ./egress-doctor.sh --proxy http://proxy.corp:8080
#   ./egress-doctor.sh --host example.com --host api.foo.com
#
# Exits 0 always — this is a diagnostic, not a gate. Read the table.
# =============================================================================
set -uo pipefail

CONNECT_TIMEOUT="${CONNECT_TIMEOUT:-6}"
MAX_TIME="${MAX_TIME:-12}"
PROXY=""
EXTRA_HOSTS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --proxy) PROXY="$2"; shift 2 ;;
    --host)  EXTRA_HOSTS+=("$2"); shift 2 ;;
    --timeout) CONNECT_TIMEOUT="$2"; shift 2 ;;
    -h|--help) sed -n '2,32p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Destinations this application actually needs, grouped by who owns the failure.
# Kept explicit rather than "test the internet": an allowlist-based egress will
# pass one and fail the next, and that difference IS the finding.
APP_HOSTS=(
  "ghcr.io|443|container registry — the UI image itself"
  "pkg-containers.githubusercontent.com|443|ghcr blob storage (pull fails without it)"
  "clinicaltrials.gov|443|Radar: trials"
  "www.ebi.ac.uk|443|Radar/ADE: Europe PMC REST"
  "europepmc.org|443|ADE: PDF fetch"
  "eutils.ncbi.nlm.nih.gov|443|Radar: PubMed E-utilities"
  "api.uspto.gov|443|Radar: patents"
  "www.sec.gov|443|Radar: EDGAR filings"
  "api.openai.com|443|chat titling (optional)"
)
AWS_HOSTS=(
  "s3.us-east-1.amazonaws.com|443|S3 — should work via the gateway endpoint"
  "bedrock-runtime.us-east-1.amazonaws.com|443|Bedrock inference"
  "ssm.us-east-1.amazonaws.com|443|Session Manager (needs endpoint or egress)"
)
CONTROL_HOSTS=(
  "1.1.1.1|443|raw IP, no DNS — separates DNS failure from path failure"
)

for h in "${EXTRA_HOSTS[@]:-}"; do [[ -n "$h" ]] && APP_HOSTS+=("$h|443|(requested)"); done

# ---------------------------------------------------------------- helpers ---
c_red=$'\033[31m'; c_grn=$'\033[32m'; c_yel=$'\033[33m'; c_dim=$'\033[2m'; c_off=$'\033[0m'
ok()   { printf '%s%-7s%s' "$c_grn" "PASS" "$c_off"; }
bad()  { printf '%s%-7s%s' "$c_red" "FAIL" "$c_off"; }
warn() { printf '%s%-7s%s' "$c_yel" "WARN" "$c_off"; }

have() { command -v "$1" >/dev/null 2>&1; }

hr() { printf '%s\n' "-------------------------------------------------------------------------------"; }

# DNS: does the resolver answer for a public name at all?
test_dns() {
  local host="$1"
  [[ "$host" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] && { echo "n/a"; return 0; }
  local ip
  if have getent; then
    ip=$(getent ahostsv4 "$host" 2>/dev/null | awk 'NR==1{print $1}')
  fi
  if [[ -z "${ip:-}" ]] && have dig; then
    ip=$(dig +short +time=3 +tries=1 "$host" A 2>/dev/null | grep -m1 -E '^[0-9]+\.')
  fi
  [[ -n "${ip:-}" ]] && { echo "$ip"; return 0; }
  echo ""; return 1
}

# TCP + TLS + HTTP in one curl, because curl's exit code already separates the
# layers and does so without depending on `timeout(1)` — which is absent on macOS
# and would otherwise make every destination look dead when it is merely untested.
#
# Exit codes that matter:
#    0            connected, TLS fine, HTTP answered
#    6            DNS
#    7            could not connect  → refused / no route (message distinguishes)
#   28            timed out          → silently dropped
#   35 51 60 58   TCP reached, TLS refused or untrusted (this is a TRUST finding)
#   56           connection reset mid-stream (inspection device dropping)
probe() {
  local host="$1" port="$2"
  local args=(-s -o /dev/null -w '%{http_code}' --connect-timeout "$CONNECT_TIMEOUT" --max-time "$MAX_TIME")
  [[ -n "$PROXY" ]] && args+=(--proxy "$PROXY")
  local scheme="https"; [[ "$port" == "80" ]] && scheme="http"
  local code rc err
  code=$(curl "${args[@]}" "$scheme://$host/" 2>/tmp/.curlerr); rc=$?
  err=$(tr -d '\n' </tmp/.curlerr 2>/dev/null)

  case "$rc" in
    0)  PROBE_TCP="open"; PROBE_HTTP="$code" ;;
    6)  PROBE_TCP="-";    PROBE_HTTP="dns" ;;
    7)  if [[ "$err" == *"refused"* ]]; then PROBE_TCP="refused"
        elif [[ "$err" == *"No route"* ]]; then PROBE_TCP="no-route"
        else PROBE_TCP="connect-fail"; fi
        PROBE_HTTP="-" ;;
    28) PROBE_TCP="timeout"; PROBE_HTTP="-" ;;
    35|51|58|60) PROBE_TCP="open"; PROBE_HTTP="tls-$rc" ;;
    56) PROBE_TCP="open"; PROBE_HTTP="reset" ;;
    *)  PROBE_TCP="curl-$rc"; PROBE_HTTP="-" ;;
  esac
}

# TLS: a corporate MITM shows up here as an unexpected issuer, which is the
# single most actionable finding — it means egress works but trust is missing.
test_tls() {
  local host="$1" port="$2"
  have openssl || { echo "no-openssl"; return 0; }
  local out
  out=$(echo | openssl s_client -connect "$host:$port" -servername "$host" 2>&1)
  if [[ "$out" != *"CONNECTED"* ]]; then echo "no-connect"; return 1; fi
  local issuer
  issuer=$(sed -n 's/^issuer=//p' <<<"$out" | head -1)
  [[ -z "$issuer" ]] && issuer=$(grep -m1 -oE 'i:.*' <<<"$out")
  if grep -qE 'verify error|self.signed|unable to get local issuer' <<<"$out"; then
    echo "UNTRUSTED issuer:${issuer:-unknown}"; return 1
  fi
  echo "ok issuer:${issuer:-unknown}"
}

probe_group() {
  local title="$1"; shift
  hr; echo "$title"; hr
  printf '%-42s %-6s %-13s %-8s %s\n' "DESTINATION" "DNS" "TCP" "HTTP" "NOTE"
  local entry host port note dns mark
  for entry in "$@"; do
    IFS='|' read -r host port note <<<"$entry"
    dns=$(test_dns "$host") || dns=""
    if [[ -z "$dns" ]]; then
      printf '%-42s %s %-13s %-8s %s\n' "$host" "$(bad)" "-" "-" "DNS did not resolve — $note"
      continue
    fi
    probe "$host" "$port"
    if [[ "$PROBE_HTTP" =~ ^[23] ]]; then mark=$(ok)
    elif [[ "$PROBE_HTTP" =~ ^4 ]]; then mark=$(warn)
    else mark=$(bad); fi
    printf '%-42s %-6s %-13s %s%-8s %s\n' "$host" "ok" "$PROBE_TCP" "$mark" "$PROBE_HTTP" "$note"
  done
}

# ------------------------------------------------------------------- report --
echo
echo "egress-doctor — $(date -u '+%Y-%m-%d %H:%M:%SZ')"
echo "host: $(hostname)  private-ip: $(hostname -I 2>/dev/null | awk '{print $1}')"
echo "proxy under test: ${PROXY:-<none — testing direct egress>}"
echo

hr; echo "0. ENVIRONMENT — is a proxy already configured, and is IMDS excluded?"; hr
for v in http_proxy https_proxy no_proxy HTTP_PROXY HTTPS_PROXY NO_PROXY; do
  printf '  %-12s = %s\n' "$v" "${!v:-<unset>}"
done
if [[ -n "${NO_PROXY:-}${no_proxy:-}" ]] && ! grep -q '169.254.169.254' <<<"${NO_PROXY:-}${no_proxy:-}"; then
  echo "  $(warn) NO_PROXY does not exclude 169.254.169.254 — the instance role will break:"
  echo "         IMDS is link-local and must never be sent to a proxy."
fi
echo "  docker daemon proxy: $(test -f /etc/systemd/system/docker.service.d/http-proxy.conf && echo present || echo '<none>')"

hr; echo "1. IMDS — proves the instance role works (S3, SSM depend on it)"; hr
if have curl; then
  tok=$(curl -s --noproxy '*' --max-time 3 -X PUT "http://169.254.169.254/latest/api/token" \
        -H "X-aws-ec2-metadata-token-ttl-seconds: 60" 2>/dev/null)
  if [[ -n "$tok" ]]; then
    role=$(curl -s --noproxy '*' --max-time 3 -H "X-aws-ec2-metadata-token: $tok" \
           http://169.254.169.254/latest/meta-data/iam/security-credentials/ 2>/dev/null)
    echo "  $(ok) IMDSv2 reachable — role: ${role:-<none attached>}"
  else
    echo "  $(warn) IMDSv2 unreachable — expected if you are NOT on the EC2 instance."
    echo "         If you ARE on it: the instance role is broken (proxy leakage, or"
    echo "         http_put_response_hop_limit too low for a container)."
  fi
fi

probe_group "2. APPLICATION DESTINATIONS — the internet this app actually needs" "${APP_HOSTS[@]}"
probe_group "3. AWS SERVICE ENDPOINTS — should work via VPC endpoints, no internet needed" "${AWS_HOSTS[@]}"
probe_group "4. CONTROL — raw IP, no DNS involved" "${CONTROL_HOSTS[@]}"

hr; echo "5. TLS INSPECTION — is a proxy substituting its own certificate?"; hr
for h in ghcr.io www.ebi.ac.uk; do
  printf '  %-24s %s\n' "$h" "$(test_tls "$h" 443)"
done
echo
echo "  An issuer that is not a public CA means egress is TLS-intercepted. That is"
echo "  not a failure to fix on the network side — install the corporate root CA in"
echo "  the instance trust store and in every container (NODE_EXTRA_CA_CERTS,"
echo "  REQUESTS_CA_BUNDLE, SSL_CERT_FILE)."
echo

hr; echo "6. VERDICT"; hr
cat <<'VERDICT'
  Read the table above, then use this mapping — it is the whole point of the run:

  * Everything in section 2 times out, section 3 passes
      → there is no internet egress at all; only the AWS VPC endpoints work.
        A security-group "port" change cannot fix this. The corporate egress
        policy for this source IP is the only lever.

  * Section 2 times out directly but passes with --proxy
      → direct egress is closed by design. Nothing is broken. The application
        must be taught to use the proxy (see infrastructure/.../variables.tf:
        http_proxy_url) — no further network-team action is needed.

  * Some hosts in section 2 pass, others time out
      → this is a destination allowlist, not a port. Give the network team the
        exact FQDN list from the failing rows; "open 443" is already true.

  * TCP "refused" rather than "timeout"
      → something is actively rejecting. That IS a firewall rule, and it is
        scoped wrongly — quote the source IP printed at the top of this report.

  * TLS shows UNTRUSTED with a corporate issuer
      → egress works and is being inspected. This is a trust-store fix on our
        side, not a network fix.
VERDICT
echo
