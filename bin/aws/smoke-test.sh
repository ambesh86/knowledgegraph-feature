#!/usr/bin/env bash
# =============================================================================
# smoke-test — verify the deployment actually works, feature by feature.
#
# Run ON the instance, immediately after a deploy:
#   aws ssm start-session --target <instance-id>
#   sudo bash /tmp/smoke-test.sh
#
# "The containers are running" is not the same as "the product works", and the
# gap between them is where every incident in this deployment has lived so far:
# a UI that starts fine while pointed at a hostname that does not resolve, an
# agent URL that 404s on every question, a scanner with no path to its sources.
# Each check here exercises the actual path a user's request takes.
#
# Exit code is the number of FAILed checks, so CI can gate on it.
# =============================================================================
set -uo pipefail

PASS=0; FAIL=0; WARN=0
c_grn=$'\033[32m'; c_red=$'\033[31m'; c_yel=$'\033[33m'; c_off=$'\033[0m'

pass() { printf "  ${c_grn}PASS${c_off}  %s\n" "$1"; PASS=$((PASS+1)); }
fail() { printf "  ${c_red}FAIL${c_off}  %s\n"   "$1"; printf "        → %s\n" "${2:-}"; FAIL=$((FAIL+1)); }
warn() { printf "  ${c_yel}WARN${c_off}  %s\n"   "$1"; printf "        → %s\n" "${2:-}"; WARN=$((WARN+1)); }
hdr()  { printf "\n%s\n%s\n" "$1" "$(printf '%.0s-' {1..70})"; }

UI_PORT="${UI_PORT:-80}"
UI="http://127.0.0.1:${UI_PORT}"
BASE_PATH="${BASE_PATH:-/nextgen}"

# --------------------------------------------------------------- containers --
hdr "1. Containers"
for c in eugene-ui atlas-postgres; do
  if docker ps --format '{{.Names}}' | grep -qx "$c"; then
    pass "$c running"
  else
    fail "$c NOT running" "docker logs $c 2>&1 | tail -40"
  fi
done
for c in eugene-scout eugene-ade; do
  if docker ps --format '{{.Names}}' | grep -qx "$c"; then
    pass "$c running"
  else
    warn "$c not running" "Radar/Evidence will be degraded. Enabled in terraform?"
  fi
done

# ------------------------------------------------------------------- the UI --
hdr "2. UI responds"
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "${UI}${BASE_PATH}/login")
case "$code" in
  200|307|308) pass "login page reachable (HTTP $code)" ;;
  000)         fail "UI not answering on port ${UI_PORT}" "systemctl status eugene-ui" ;;
  *)           fail "login page HTTP $code" "docker logs eugene-ui | tail -40" ;;
esac

# ------------------------------------------------------------------ database --
hdr "3. Database — reachable AND persistent"
if docker exec atlas-postgres pg_isready -U atlas >/dev/null 2>&1; then
  pass "postgres accepting connections"
  users=$(docker exec atlas-postgres psql -U atlas -d atlas -tAc \
          "select count(*) from users" 2>/dev/null || echo "?")
  if [[ "$users" == "?" ]]; then
    warn "users table not found" "First boot is fine; after a restore it is not."
  else
    pass "users table present ($users rows)"
  fi
else
  fail "postgres not ready" "docker logs atlas-postgres | tail -40"
fi

# The check that catches the data-loss bug: is the data on the persistent
# volume, or on the root disk where the next deploy will destroy it?
src=$(docker inspect atlas-postgres --format '{{range .Mounts}}{{.Source}} {{end}}' 2>/dev/null)
if grep -q '/mnt/atlas-data' <<<"$src"; then
  pass "database is on the persistent EBS volume"
elif [[ -n "$src" ]]; then
  fail "database is NOT on the persistent volume ($src)" \
       "The next deploy replaces the instance and DELETES all users and history. Set persist_atlas_data = true."
fi

# -------------------------------------------------------------- backend ALB --
hdr "4. Backend (the path an Ask request takes)"
ALB=$(docker exec eugene-ui printenv EUGENE_CORE_API_URL 2>/dev/null)
AGENT=$(docker exec eugene-ui printenv EUGENE_AGENT_API_URL 2>/dev/null)

if [[ -z "$ALB" || "$ALB" == *"eugene_ws"* ]]; then
  fail "EUGENE_CORE_API_URL is unset or still the compose default ($ALB)" \
       "Graph, digest and freshness will all fail. Set eugene_alb_base."
else
  code=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 10 "$ALB/health" 2>/dev/null)
  [[ "$code" =~ ^[23] ]] && pass "core API reachable ($code)" \
    || fail "core API unreachable from the box (HTTP $code)" "curl -vk $ALB/health"
fi

# The exact misconfiguration that breaks every question asked.
if [[ "$AGENT" == *"/query/stream"* ]]; then
  fail "EUGENE_AGENT_API_URL ends in /query/stream" \
       "The UI appends it again → 404 on every question. Use the base .../agent/api."
elif [[ -z "$AGENT" || "$AGENT" == *"eugene_agent_ws"* ]]; then
  fail "EUGENE_AGENT_API_URL unset or compose default ($AGENT)" "Ask will not work."
else
  code=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 10 "$AGENT/health" 2>/dev/null)
  [[ "$code" =~ ^[234] ]] && pass "agent API reachable ($code)" \
    || warn "agent /health returned $code" "May be normal if it exposes no /health."
fi

# -------------------------------------------------------- scout / ade wiring --
hdr "5. Radar and Evidence"
SCOUT=$(docker exec eugene-ui printenv EUGENE_SCOUT_URL 2>/dev/null)
ADE=$(docker exec eugene-ui printenv EUGENE_ADE_URL 2>/dev/null)

check_service() {
  local name="$1" envvar="$2" url="$3" feature="$4"
  if [[ -z "$url" || "$url" == *"eugene_scout"* || "$url" == *"eugene_ade"* ]]; then
    fail "$envvar is unset or the compose default (${url:-<unset>})" \
         "$feature will show the degraded state — that hostname does not resolve here."
  elif [[ "$url" == *"127.0.0.1:1"* ]]; then
    warn "$name is disabled in terraform" "$feature is degraded by design."
  else
    local code
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url/health" 2>/dev/null)
    if [[ "$code" =~ ^[23] ]]; then
      pass "$name healthy ($code)"
    else
      fail "$name unreachable at $url (HTTP $code)" "docker logs eugene-$name | tail -30"
    fi
  fi
}

check_service scout EUGENE_SCOUT_URL "$SCOUT" "Radar/Watchlist/Today/Briefing"
check_service ade   EUGENE_ADE_URL   "$ADE"   "Evidence pages"

# ------------------------------------------------------------------- egress --
hdr "6. Outbound internet (only Scout and ADE need it)"
code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 6 --max-time 12 \
       https://clinicaltrials.gov/ 2>/dev/null)
if [[ "$code" =~ ^[23] ]]; then
  pass "internet egress works (clinicaltrials.gov $code)"
else
  warn "no direct internet egress" \
       "Scanning and PDF fetch cannot work. Run egress-doctor.sh for the layer-by-layer verdict."
fi

# ---------------------------------------------------------------- IAM / S3 ---
hdr "7. Instance role"
if curl -s --noproxy '*' --max-time 3 -X PUT "http://169.254.169.254/latest/api/token" \
     -H "X-aws-ec2-metadata-token-ttl-seconds: 60" >/dev/null 2>&1; then
  pass "IMDS reachable — instance role intact"
else
  fail "IMDS unreachable" "S3 access will fail. Check NO_PROXY includes 169.254.169.254."
fi

printf "\n%s\n" "$(printf '%.0s=' {1..70})"
printf "  %d passed, %d failed, %d warnings\n" "$PASS" "$FAIL" "$WARN"
if (( FAIL > 0 )); then
  printf "  ${c_red}NOT deployable-clean — fix the FAILs above.${c_off}\n\n"
else
  printf "  ${c_grn}All hard checks passed.${c_off}\n\n"
fi
exit "$FAIL"
