<#
.SYNOPSIS
  Run one Scout scan from a Windows VDI and write the results to S3.

.DESCRIPTION
  The fetching half of the split deployment, for hosts where Docker is not
  permitted. Runs the scanner as a plain Python process — five pure-Python
  dependencies, no container, no build toolchain.

  Point Windows Task Scheduler at this file to get a daily scan. Use the
  platform scheduler rather than a cron inside the app: a VDI reboots and logs
  out, and a schedule that only exists inside a process that is not running is a
  schedule that silently never fires.

  Exits non-zero when the scan fails, so a broken run shows as a failed task
  instead of a green tick over a bucket that never got written.

.PARAMETER Areas
  Limit to specific research areas. Default: every enabled area.

.EXAMPLE
  .\run-scan.ps1
  .\run-scan.ps1 -Areas hemophilia,immunoglobulin

.NOTES
  First-time setup (once per machine):

    git clone https://github.com/aisemanticexpert/knowledgegraph.git
    cd knowledgegraph
    python -m venv .venv
    .venv\Scripts\pip install -r agents\eugene-scout\requirements-fetcher.txt
    aws sso login --profile eugene-deploy

  Behind a corporate proxy, pip needs telling separately — it does not read the
  system proxy on Windows:

    .venv\Scripts\pip install --proxy http://proxy.corp:8080 -r agents\eugene-scout\requirements-fetcher.txt
#>
[CmdletBinding()]
param(
  [string[]] $Areas,
  [string]   $Bucket     = $env:SCOUT_S3_BUCKET,
  [string]   $Region     = "us-east-1",
  [string]   $AwsProfile = "eugene-deploy"
)

$ErrorActionPreference = "Stop"

# Repo root is two levels up from bin\vdi. Resolved from the script's own
# location so Task Scheduler can invoke it with any working directory — the
# default there is C:\Windows\System32, which would otherwise break every
# relative path in this file.
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$SrcPath  = Join-Path $RepoRoot "agents\eugene-scout\src"
$Python   = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
  Write-Error "No virtualenv at $Python. Run the first-time setup in the NOTES section of this file."
  exit 2
}
if ([string]::IsNullOrWhiteSpace($Bucket)) {
  Write-Error "Set -Bucket or `$env:SCOUT_S3_BUCKET. It must match the bucket the AWS deployment reads (scout_s3_bucket in terraform.tfvars) or the two halves will never meet."
  exit 2
}

$env:PYTHONPATH         = $SrcPath
$env:SCOUT_S3_BUCKET    = $Bucket
$env:AWS_REGION         = $Region
$env:AWS_PROFILE        = $AwsProfile
# This host is the one WITH internet — it is the half that scans.
$env:SCOUT_SCAN_ENABLED = "true"

# Identify ourselves. A contact-bearing User-Agent is a hard requirement at SEC
# and a stated courtesy at NCBI and EBI; anonymous clients get throttled.
if (-not $env:SCOUT_USER_AGENT) {
  $env:SCOUT_USER_AGENT = "CSL-Atlas-Scout/1.0 (biomedical BD intelligence; VDI fetcher)"
}

Write-Host "Scout fetch  bucket=$Bucket  region=$Region  profile=$AwsProfile"

# Credentials must be checked before the scan, not after: an expired SSO token
# lets the whole scan run and then fails on the final write, throwing away
# several minutes of work against rate-limited public APIs.
try {
  $who = aws sts get-caller-identity --profile $AwsProfile --query Arn --output text 2>&1
  if ($LASTEXITCODE -ne 0) { throw $who }
  Write-Host "AWS identity: $who"
} catch {
  Write-Error "AWS credentials are not usable. Run: aws sso login --profile $AwsProfile"
  exit 2
}

$scanArgs = @("-m", "scout.cli", "scan")
if ($Areas) { $scanArgs += "--areas"; $scanArgs += $Areas }

& $Python @scanArgs
$code = $LASTEXITCODE

if ($code -eq 0) {
  Write-Host "Scan complete. The AWS deployment picks this up at its next index refresh (<=10 min)."
} else {
  Write-Error "Scan failed with exit code $code."
}
exit $code
