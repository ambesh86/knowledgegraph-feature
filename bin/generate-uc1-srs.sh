#!/usr/bin/env bash
#
# Regenerate the Use Case 1 SRS & Solution PDF from the LIVE system.
#
# The document contains real company names, real patents and real publications, so it
# is only meaningful when generated against a running scanner. This script pulls the
# data and then builds the PDF; the generator refuses to run against missing data
# rather than emitting plausible-looking placeholders.
#
#   ./bin/generate-uc1-srs.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SCOUT="${SCOUT_URL:-http://localhost:18300}"
DATA=/tmp/uc1doc
mkdir -p "$DATA"

TOKEN="$(grep '^SCOUT_API_TOKEN=' docker.env 2>/dev/null | cut -d= -f2- || true)"
AUTH=(); [[ -n "$TOKEN" ]] && AUTH=(-H "Authorization: Bearer $TOKEN")

echo "== pulling live data from $SCOUT =="
curl -sf "${AUTH[@]}" "$SCOUT/health" >/dev/null \
  || { echo "ERROR: scanner unreachable at $SCOUT. Start it with: docker compose up -d eugene_scout"; exit 1; }

fetch() { # fetch <query> <name>
  curl -sf "${AUTH[@]}" "$SCOUT/$1" -o "$DATA/$2.json" --max-time 60 \
    || { echo "ERROR: failed to fetch /$1"; exit 1; }
  printf '  %-12s %s bytes\n' "$2" "$(wc -c < "$DATA/$2.json" | tr -d ' ')"
}

fetch "signals?limit=500"   signals
fetch "companies?limit=200" companies
fetch "status"              status
fetch "freshness"           freshness
fetch "runs?limit=10"       runs
fetch "config"              config
fetch "areas"               areas

# One briefing per scanned area. Missing ones are skipped by the generator rather
# than failing the build — an area with no data yet is a legitimate state.
for a in $(python3 -c "import json;print(' '.join(x['id'] for x in json.load(open('$DATA/areas.json'))['areas']))"); do
  curl -sf "${AUTH[@]}" "$SCOUT/digest?area=$a" -o "$DATA/digest_$a.json" --max-time 60 || true
done
echo "  digests      $(ls "$DATA"/digest_*.json 2>/dev/null | wc -l | tr -d ' ')"

echo
echo "== rendering Mermaid diagrams =="
# Diagram source is reviewable text under version control; the PNGs are build
# artefacts. Skipped automatically if mermaid-cli cannot be fetched (offline), in
# which case the existing PNGs are reused and the PDF still builds.
if npx --yes @mermaid-js/mermaid-cli@11 --version >/dev/null 2>&1; then
  for f in docs/diagrams/*.mmd; do
    out="${f%.mmd}.png"
    npx --yes @mermaid-js/mermaid-cli@11 -i "$f" -o "$out" \
        -c docs/diagrams/mermaid-config.json -b white -s 3 --quiet >/dev/null 2>&1
    printf '  %-40s %s\n' "$(basename "$out")" "$([ -f "$out" ] && echo ok || echo FAILED)"
  done
else
  echo "  mermaid-cli unavailable — reusing the committed PNGs"
fi

echo
echo "== building PDF =="
python3 generate_uc1_srs.py
