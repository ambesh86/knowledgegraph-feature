#!/usr/bin/env bash
#
# Provision a least-privilege IAM identity for eugene_scout.
#
# WHY THIS EXISTS
# ---------------
# The scanner container authenticates to S3 with the access keys of
# `difflabs-website-deployment` — a shared IAM user that can also read the CSL
# lakehouse and the neo4j bucket. Verified: from inside the container, that identity
# lists `csl-diffusionlabs-d-s3-use1-lakehouse-001` successfully. A credential leak
# from a service whose entire job is reading four public APIs would therefore expose
# data that service has no business seeing.
#
# This script creates a dedicated user scoped to the scout bucket and nothing else.
#
# WHAT IT DOES
#   1. Creates the managed policy in eugene-scout-s3-policy.json (or updates it)
#   2. Creates the IAM user `eugene-scout`
#   3. Attaches the policy
#   4. Mints access keys and writes them into docker.env (gitignored)
#
# It is idempotent: re-running detects existing resources and only fills gaps. It
# refuses to mint a second key pair if the user already has two, because IAM caps
# users at two and silently failing there is worse than stopping.
#
# RUN IT WITH AN ADMIN CREDENTIAL. The scanner's own key deliberately cannot do this
# — that is the point of the exercise.
#
#   AWS_PROFILE=<admin> ./infrastructure/iam/provision-scout-iam.sh
#
set -euo pipefail

USER_NAME="eugene-scout"
POLICY_NAME="EugeneScoutS3Access"
BUCKET="eugene-scout-087084717211"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
POLICY_FILE="$HERE/eugene-scout-s3-policy.json"
ENV_FILE="$REPO_ROOT/docker.env"

say() { printf '  %s\n' "$*"; }
die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

echo "── preflight ──"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text 2>/dev/null)" \
  || die "no usable AWS credentials on this shell"
CALLER="$(aws sts get-caller-identity --query Arn --output text)"
say "account : $ACCOUNT"
say "caller  : $CALLER"

# Fail early and clearly rather than half-provisioning and leaving a user with no
# policy attached.
aws iam list-users --max-items 1 >/dev/null 2>&1 \
  || die "this identity cannot call IAM. Re-run with an admin profile:
         AWS_PROFILE=<admin> $0"

[[ -f "$POLICY_FILE" ]] || die "policy file missing: $POLICY_FILE"
POLICY_ARN="arn:aws:iam::${ACCOUNT}:policy/${POLICY_NAME}"

echo
echo "── policy ──"
if aws iam get-policy --policy-arn "$POLICY_ARN" >/dev/null 2>&1; then
  # Versions are capped at five; prune the oldest non-default before adding one.
  OLD="$(aws iam list-policy-versions --policy-arn "$POLICY_ARN" \
        --query 'Versions[?!IsDefaultVersion]|[-1].VersionId' --output text 2>/dev/null || echo None)"
  if [[ "$OLD" != "None" && -n "$OLD" ]]; then
    COUNT="$(aws iam list-policy-versions --policy-arn "$POLICY_ARN" --query 'length(Versions)' --output text)"
    if [[ "$COUNT" -ge 5 ]]; then
      aws iam delete-policy-version --policy-arn "$POLICY_ARN" --version-id "$OLD" >/dev/null
      say "pruned old policy version $OLD"
    fi
  fi
  aws iam create-policy-version --policy-arn "$POLICY_ARN" \
    --policy-document "file://$POLICY_FILE" --set-as-default >/dev/null
  say "updated $POLICY_NAME"
else
  aws iam create-policy --policy-name "$POLICY_NAME" \
    --policy-document "file://$POLICY_FILE" \
    --description "Least-privilege S3 access for the eugene_scout BD scanner" >/dev/null
  say "created $POLICY_NAME"
fi
say "arn     : $POLICY_ARN"

echo
echo "── user ──"
if aws iam get-user --user-name "$USER_NAME" >/dev/null 2>&1; then
  say "user $USER_NAME already exists"
else
  aws iam create-user --user-name "$USER_NAME" \
    --tags Key=Service,Value=eugene-scout Key=ManagedBy,Value=provision-scout-iam.sh >/dev/null
  say "created user $USER_NAME"
fi

aws iam attach-user-policy --user-name "$USER_NAME" --policy-arn "$POLICY_ARN"
say "attached $POLICY_NAME"

echo
echo "── access key ──"
EXISTING="$(aws iam list-access-keys --user-name "$USER_NAME" --query 'length(AccessKeyMetadata)' --output text)"
if [[ "$EXISTING" -ge 2 ]]; then
  die "$USER_NAME already has 2 access keys (the IAM maximum).
         Delete one first:
           aws iam list-access-keys --user-name $USER_NAME
           aws iam delete-access-key --user-name $USER_NAME --access-key-id <id>"
fi

KEY_JSON="$(aws iam create-access-key --user-name "$USER_NAME")"
KEY_ID="$(printf '%s' "$KEY_JSON" | python3 -c 'import json,sys;print(json.load(sys.stdin)["AccessKey"]["AccessKeyId"])')"
KEY_SECRET="$(printf '%s' "$KEY_JSON" | python3 -c 'import json,sys;print(json.load(sys.stdin)["AccessKey"]["SecretAccessKey"])')"
say "created key ${KEY_ID:0:8}… (secret written to docker.env, not printed)"

echo
echo "── docker.env ──"
[[ -f "$ENV_FILE" ]] || die "docker.env not found at $ENV_FILE"
cp "$ENV_FILE" "$ENV_FILE.bak.$(date +%s)"

# Rewrite in place. The scanner is the only service that should use this identity, so
# the keys are written as SCOUT_AWS_* and mapped onto AWS_* for that container alone
# in docker-compose.yml — replacing the global AWS_* would hand the scoped key to
# eugene_ade too, which legitimately needs the ADE bucket this policy denies.
python3 - "$ENV_FILE" "$KEY_ID" "$KEY_SECRET" <<'PY'
import pathlib, re, sys
path, key_id, secret = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
text = path.read_text()
for name, value in (("SCOUT_AWS_ACCESS_KEY_ID", key_id), ("SCOUT_AWS_SECRET_ACCESS_KEY", secret)):
    pattern = re.compile(rf'^{name}=.*$', re.MULTILINE)
    if pattern.search(text):
        text = pattern.sub(f'{name}={value}', text)
    else:
        text = text.rstrip("\n") + f"\n{name}={value}\n"
path.write_text(text)
print(f"  wrote SCOUT_AWS_ACCESS_KEY_ID / SCOUT_AWS_SECRET_ACCESS_KEY into {path.name}")
PY

cat <<EOF

── done ──
  Next:
    docker compose up -d --force-recreate eugene_scout
    ./infrastructure/iam/verify-scout-iam.sh

  The old shared key is still in docker.env for the other services. Once you are
  satisfied the scanner works on its own identity, consider whether
  difflabs-website-deployment still needs to be used by this stack at all.
EOF
