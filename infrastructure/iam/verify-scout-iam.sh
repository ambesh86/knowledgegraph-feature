#!/usr/bin/env bash
#
# Verify the scanner is running on its scoped identity — from inside the container,
# which is the only place the answer means anything.
#
# The checks are deliberately two-sided. Confirming the scanner can still reach its
# own bucket proves nothing about least privilege; the assertions that matter are the
# ones that must FAIL. A policy that grants what it should and also everything else
# passes every positive test.
#
#   ./infrastructure/iam/verify-scout-iam.sh
#
set -uo pipefail

CONTAINER="eugene-scout"
BUCKET="eugene-scout-087084717211"
# Buckets this service has no business touching. The first was verified reachable
# from inside the container on the shared key.
FORBIDDEN=(
  "csl-diffusionlabs-d-s3-use1-lakehouse-001"
  "neo4-eugene"
  "eugene-research-pdfs-087084717211"
)

pass=0; fail=0
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; pass=$((pass+1)); }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$*"; fail=$((fail+1)); }

in_container() { docker exec "$CONTAINER" python -c "$1" 2>&1; }

docker ps --format '{{.Names}}' | grep -qx "$CONTAINER" \
  || { echo "ERROR: $CONTAINER is not running"; exit 1; }

echo "── identity ──"
ARN="$(in_container "
import boto3
try: print(boto3.client('sts').get_caller_identity()['Arn'])
except Exception as e: print('ERROR', e)
" | tail -1)"
printf '  %s\n' "$ARN"
case "$ARN" in
  *user/eugene-scout) ok "running as the dedicated scoped user" ;;
  *difflabs*)         bad "still using the shared difflabs key — recreate the container" ;;
  *)                  bad "unexpected identity" ;;
esac

echo
echo "── it can do its job ──"
for op in \
  "list:import boto3;boto3.client('s3').list_objects_v2(Bucket='$BUCKET',MaxKeys=1);print('OK')" \
  "read:import boto3;boto3.client('s3').get_object(Bucket='$BUCKET',Key='_probe/healthcheck.txt');print('OK')" \
  "write:import boto3;boto3.client('s3').put_object(Bucket='$BUCKET',Key='_probe/iam-verify.txt',Body=b'ok');print('OK')" \
  "delete:import boto3;boto3.client('s3').delete_object(Bucket='$BUCKET',Key='_probe/iam-verify.txt');print('OK')"
do
  label="${op%%:*}"; code="${op#*:}"
  if [[ "$(in_container "$code" | tail -1)" == "OK" ]]; then ok "$label on $BUCKET"; else bad "$label on $BUCKET FAILED"; fi
done

echo
echo "── it cannot do anything else (the checks that matter) ──"
for b in "${FORBIDDEN[@]}"; do
  out="$(in_container "
import boto3
try:
    boto3.client('s3').list_objects_v2(Bucket='$b',MaxKeys=1); print('REACHABLE')
except Exception as e: print('DENIED' if 'AccessDenied' in str(e) or 'Forbidden' in str(e) else f'OTHER: {e}')
" | tail -1)"
  case "$out" in
    DENIED)    ok "denied on $b" ;;
    REACHABLE) bad "STILL REACHABLE: $b — the scoped policy is not in effect" ;;
    *)         bad "$b -> $out" ;;
  esac
done

out="$(in_container "
import boto3
try:
    boto3.client('iam').list_users(MaxItems=1); print('REACHABLE')
except Exception as e: print('DENIED' if 'AccessDenied' in str(e) or 'not authorized' in str(e) else f'OTHER: {e}')
" | tail -1)"
[[ "$out" == "DENIED" ]] && ok "denied on IAM" || bad "IAM -> $out"

echo
echo "── the service itself is healthy on the new identity ──"
if curl -sf localhost:18300/health | grep -q '"reachable": *true'; then
  ok "/health reports S3 reachable"
else
  bad "/health does not report S3 reachable"
fi

echo
printf '  %d passed, %d failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]] || exit 1
