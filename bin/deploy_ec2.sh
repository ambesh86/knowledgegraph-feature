#!/usr/bin/env bash
# =============================================================================
# Eugene — single-file EC2 bootstrap & deploy
# =============================================================================
# Brings up the full Eugene stack (Neo4j + core API + MCP + agent + chat UI)
# on a fresh EC2 instance. Idempotent: re-running upgrades in place.
#
# SUPPORTED OS
#   - Amazon Linux 2023            (recommended)
#   - Ubuntu 22.04 / 24.04 LTS
#
# RECOMMENDED EC2 SHAPE
#   - t3.large or larger           (4 GB RAM is the floor)
#   - 30 GB gp3 EBS root volume
#   - Security group: open 22 (you only),
#                     17474, 18000, 18001, 18443, 18501 (you only or VPN)
#
# USAGE — three ways
# -----------------------------------------------------------------------------
# 1) As EC2 user-data (paste into "Advanced details > User data" at launch):
#      #!/usr/bin/env bash
#      export ANTHROPIC_API_KEY=sk-ant-...
#      export EUGENE_REPO=https://github.com/<you>/knowledgeGraph.git
#      curl -fsSL https://raw.githubusercontent.com/<you>/knowledgeGraph/main/bin/deploy_ec2.sh | bash
#
# 2) SSH in, clone the repo, run from the repo root:
#      git clone <repo> && cd knowledgeGraph
#      ANTHROPIC_API_KEY=sk-ant-... ./bin/deploy_ec2.sh
#
# 3) SSH in, run directly (script will clone for you):
#      ANTHROPIC_API_KEY=sk-ant-... EUGENE_REPO=<git-url> bash deploy_ec2.sh
#
# ENVIRONMENT VARIABLES (read by this script)
# -----------------------------------------------------------------------------
#   ANTHROPIC_API_KEY        (one of these two required, unless using Bedrock)
#   OPENAI_API_KEY
#   LLM_PROVIDER             "anthropic" | "openai" | "bedrock"   (default: auto)
#   NEO4J_PASSWORD           default: eugene_local_2024
#   EUGENE_CLIENT_SECRET     default: random 48-char string
#   EUGENE_REPO              git URL to clone if /opt/eugene is missing
#   EUGENE_BRANCH            default: main
#   EUGENE_DIR               default: /opt/eugene
#   PUBLIC_HOSTNAME          if set, used in the printed URLs
# =============================================================================

set -Eeuo pipefail

# ---------- helpers ----------------------------------------------------------
log()  { printf "\n\033[1;34m[eugene]\033[0m %s\n" "$*"; }
warn() { printf "\n\033[1;33m[eugene]\033[0m %s\n" "$*" >&2; }
die()  { printf "\n\033[1;31m[eugene]\033[0m %s\n" "$*" >&2; exit 1; }

need_root() {
  if [[ $EUID -ne 0 ]]; then
    if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; else die "must run as root or have sudo"; fi
  else
    SUDO=""
  fi
}

detect_os() {
  if [[ -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    OS_ID="${ID:-unknown}"
    OS_VER="${VERSION_ID:-unknown}"
  else
    die "cannot detect OS — /etc/os-release missing"
  fi
  log "detected OS: $OS_ID $OS_VER"
}

rand_secret() {
  if command -v openssl >/dev/null 2>&1; then openssl rand -hex 24
  else head -c 48 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 48
  fi
}

# ---------- defaults ---------------------------------------------------------
EUGENE_DIR="${EUGENE_DIR:-/opt/eugene}"
EUGENE_BRANCH="${EUGENE_BRANCH:-main}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-eugene_local_2024}"
EUGENE_CLIENT_SECRET="${EUGENE_CLIENT_SECRET:-$(rand_secret)}"
LLM_PROVIDER="${LLM_PROVIDER:-}"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"
ANTHROPIC_MODEL_ID="${ANTHROPIC_MODEL_ID:-claude-sonnet-4-20250514}"
OPENAI_MODEL_ID="${OPENAI_MODEL_ID:-gpt-4.1-mini}"

# auto-detect LLM provider if not set
if [[ -z "$LLM_PROVIDER" ]]; then
  if   [[ -n "$ANTHROPIC_API_KEY" ]]; then LLM_PROVIDER="anthropic"
  elif [[ -n "$OPENAI_API_KEY"    ]]; then LLM_PROVIDER="openai"
  else
    warn "no API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY, or LLM_PROVIDER=bedrock."
    LLM_PROVIDER="anthropic"
  fi
fi

# ---------- OS-specific install -------------------------------------------
install_packages_amazon() {
  log "installing packages on Amazon Linux"
  $SUDO dnf -y update
  $SUDO dnf -y install docker git jq openssl
  $SUDO systemctl enable --now docker
  if ! command -v docker-compose >/dev/null 2>&1; then
    # Compose v2 plugin
    $SUDO mkdir -p /usr/local/lib/docker/cli-plugins
    COMPOSE_VER="v2.29.7"
    $SUDO curl -fsSL \
      "https://github.com/docker/compose/releases/download/${COMPOSE_VER}/docker-compose-linux-$(uname -m)" \
      -o /usr/local/lib/docker/cli-plugins/docker-compose
    $SUDO chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
  fi
  # let ec2-user run docker without sudo on next login
  $SUDO usermod -aG docker ec2-user 2>/dev/null || true
}

install_packages_ubuntu() {
  log "installing packages on Ubuntu"
  export DEBIAN_FRONTEND=noninteractive
  $SUDO apt-get update -y
  $SUDO apt-get install -y ca-certificates curl gnupg git jq openssl
  $SUDO install -m 0755 -d /etc/apt/keyrings
  if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
      $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    $SUDO chmod a+r /etc/apt/keyrings/docker.gpg
  fi
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | $SUDO tee /etc/apt/sources.list.d/docker.list >/dev/null
  $SUDO apt-get update -y
  $SUDO apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  $SUDO systemctl enable --now docker
  $SUDO usermod -aG docker ubuntu 2>/dev/null || true
}

install_packages() {
  case "$OS_ID" in
    amzn)             install_packages_amazon ;;
    ubuntu)           install_packages_ubuntu ;;
    debian)           install_packages_ubuntu ;;
    *) die "unsupported OS: $OS_ID. Install Docker manually and re-run." ;;
  esac
}

# ---------- repo bring-down -------------------------------------------------
ensure_repo() {
  if [[ -d "$EUGENE_DIR/.git" ]]; then
    log "repo present at $EUGENE_DIR — pulling latest on $EUGENE_BRANCH"
    $SUDO git -C "$EUGENE_DIR" fetch --all --prune
    $SUDO git -C "$EUGENE_DIR" checkout "$EUGENE_BRANCH"
    $SUDO git -C "$EUGENE_DIR" pull --ff-only
    return
  fi
  if [[ -z "${EUGENE_REPO:-}" ]]; then
    # If the script was launched from inside an already-cloned repo, just use it
    if [[ -f "$(pwd)/docker-compose.yml" ]]; then
      EUGENE_DIR="$(pwd)"
      log "using current directory $EUGENE_DIR as the repo"
      return
    fi
    die "EUGENE_REPO is unset and $EUGENE_DIR is empty. Set EUGENE_REPO=<git-url>."
  fi
  log "cloning $EUGENE_REPO -> $EUGENE_DIR (branch $EUGENE_BRANCH)"
  $SUDO mkdir -p "$(dirname "$EUGENE_DIR")"
  $SUDO git clone --branch "$EUGENE_BRANCH" "$EUGENE_REPO" "$EUGENE_DIR"
}

# ---------- env file ---------------------------------------------------------
write_env_file() {
  local target="$EUGENE_DIR/docker.env"
  log "writing $target"
  $SUDO tee "$target" >/dev/null <<EOF
# Auto-generated by deploy_ec2.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
# Edit and re-run \`docker compose up -d\` to apply.

# --- Neo4j ---
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=${NEO4J_PASSWORD}

# --- Eugene JWT signing (shared across services) ---
EUGENE_TENANT_ID=f8645748-68c6-4eec-bd61-c71341a6ed7d
EUGENE_CLIENT_ID=ff58ded5-c309-4cc8-ae6a-3b7157b83879
EUGENE_CLIENT_SECRET=${EUGENE_CLIENT_SECRET}

# --- LLM provider ---
LLM_PROVIDER=${LLM_PROVIDER}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
ANTHROPIC_MODEL_ID=${ANTHROPIC_MODEL_ID}
OPENAI_API_KEY=${OPENAI_API_KEY}
OPENAI_MODEL_ID=${OPENAI_MODEL_ID}

# --- Runtime mode ---
ENVIRONMENT=local

# --- Agent allowlist (empty = allow all UPNs in local mode) ---
EUGENE_AGENT_ALLOWED_UPNS=
EOF
  $SUDO chmod 600 "$target"
}

# ---------- compose up -------------------------------------------------------
compose_up() {
  log "starting docker compose stack from $EUGENE_DIR"
  cd "$EUGENE_DIR"
  $SUDO docker compose --env-file docker.env pull || true
  $SUDO docker compose --env-file docker.env up --build -d
  log "stack started. Tail logs with:  sudo docker compose -f $EUGENE_DIR/docker-compose.yml logs -f"
}

# ---------- health probe -----------------------------------------------------
wait_for_health() {
  log "waiting up to 5 minutes for Neo4j + core API to become healthy"
  local deadline=$(( $(date +%s) + 300 ))
  while [[ $(date +%s) -lt $deadline ]]; do
    if curl -fsS "http://localhost:17474" >/dev/null 2>&1; then
      log "Neo4j browser is up"
      break
    fi
    sleep 5
  done
  while [[ $(date +%s) -lt $deadline ]]; do
    if curl -fsS "http://localhost:18000/docs" >/dev/null 2>&1; then
      log "core API is up"
      return
    fi
    sleep 5
  done
  warn "services did not become healthy within 5 min — check 'docker compose logs'"
}

# ---------- print summary ----------------------------------------------------
print_urls() {
  local host="${PUBLIC_HOSTNAME:-}"
  if [[ -z "$host" ]]; then
    host="$(curl -fsS http://169.254.169.254/latest/meta-data/public-hostname 2>/dev/null || true)"
  fi
  if [[ -z "$host" ]]; then host="<this-ec2-public-dns>"; fi

  cat <<EOF

============================================================
  Eugene is up. Reach the services at:
============================================================

  Chat UI (Streamlit)   http://${host}:18501
  Agent API docs        http://${host}:18001/docs
  Core API docs         http://${host}:18000/docs
  MCP server            http://${host}:18443
  Neo4j Browser         http://${host}:17474
        (login: neo4j / ${NEO4J_PASSWORD})

  Compose dir:          ${EUGENE_DIR}
  Env file:             ${EUGENE_DIR}/docker.env  (chmod 600)
  LLM provider:         ${LLM_PROVIDER}

  Useful commands:
    sudo docker compose -f ${EUGENE_DIR}/docker-compose.yml ps
    sudo docker compose -f ${EUGENE_DIR}/docker-compose.yml logs -f eugene_agent_ws
    sudo docker compose -f ${EUGENE_DIR}/docker-compose.yml restart eugene_mcp
    sudo docker compose -f ${EUGENE_DIR}/docker-compose.yml down            # stop, keep data
    sudo docker compose -f ${EUGENE_DIR}/docker-compose.yml down -v          # stop and WIPE Neo4j

  Security reminder:
    Lock ports 17474/18000/18001/18443/18501 in your security group
    to your IP or VPN. They are unauthenticated in local mode.
============================================================
EOF
}

# ---------- main -------------------------------------------------------------
main() {
  need_root
  detect_os
  install_packages
  ensure_repo
  write_env_file
  compose_up
  wait_for_health
  print_urls
}

main "$@"
