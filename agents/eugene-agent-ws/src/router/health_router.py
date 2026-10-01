"""Deep health check with dependency validation (OBS-04).

/health           — liveness only, fast & cheap (for Docker/ELB)
/health/ready     — readiness: validates MCP reachability + LLM key presence
"""
import logging
import os
import time
from typing import Any

import httpx
import boto3
from fastapi import APIRouter, Response, status

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["health"],
)


@router.get("/health")
async def liveness() -> dict[str, Any]:
    return {"status": "OK", "service": "eugene-agent-ws"}


@router.get("/health/ready")
async def readiness(response: Response) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}
    overall_ok = True

    # 1. Check static configuration and the AWS credential chain without invoking a model.
    aliases = {"aws": "bedrock", "claude": "anthropic", "gpt": "openai"}
    provider = aliases.get(os.environ.get("LLM_PROVIDER", "bedrock").strip().lower(),
                           os.environ.get("LLM_PROVIDER", "bedrock").strip().lower())
    fallback_provider_raw = os.environ.get("LLM_FALLBACK_PROVIDER", "").strip().lower()
    fallback_provider = aliases.get(fallback_provider_raw, fallback_provider_raw)

    def provider_ready(name: str) -> tuple[bool, dict[str, Any]]:
        if name == "bedrock":
            try:
                session = boto3.Session()
                credentials_available = session.get_credentials() is not None
                region = (
                    os.environ.get("AWS_REGION")
                    or os.environ.get("AWS_DEFAULT_REGION")
                    or session.region_name
                )
                return credentials_available and bool(region), {
                    "credentials_available": credentials_available,
                    "region": region,
                }
            except Exception as exc:
                return False, {"error": type(exc).__name__}
        if name == "anthropic":
            configured = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
            return configured, {"api_key_configured": configured}
        if name == "openai":
            configured = bool(os.environ.get("OPENAI_API_KEY", "").strip())
            return configured, {"api_key_configured": configured}
        return False, {"error": "unsupported provider"}

    primary_ok, primary_details = provider_ready(provider)
    llm_check: dict[str, Any] = {
        "ok": primary_ok,
        "provider": provider,
        "primary": primary_details,
    }
    if fallback_provider:
        fallback_ok, fallback_details = provider_ready(fallback_provider)
        llm_check["fallback_provider"] = fallback_provider
        llm_check["fallback"] = fallback_details
        llm_check["ok"] = primary_ok and fallback_ok and fallback_provider != provider
    checks["llm_provider"] = llm_check
    overall_ok &= checks["llm_provider"]["ok"]

    # 2. MCP server reachability
    mcp_url = os.environ.get("EUGENE_MCP_SERVER_URL", "")
    if mcp_url:
        start = time.perf_counter()
        try:
            # Probe the root of the MCP server (strip /mcp suffix if present)
            probe_url = mcp_url.rstrip("/")
            if probe_url.endswith("/mcp"):
                probe_url = probe_url[:-4]
            verify_ssl = os.environ.get("EUGENE_MCP_VERIFY_SSL", "true").lower() != "false"
            async with httpx.AsyncClient(verify=verify_ssl, timeout=3.0) as client:
                resp = await client.get(f"{probe_url}/health")
            checks["mcp"] = {
                "ok": resp.status_code < 500,
                "status_code": resp.status_code,
                "latency_ms": int((time.perf_counter() - start) * 1000),
            }
        except Exception as exc:
            checks["mcp"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        overall_ok &= checks["mcp"]["ok"]
    else:
        checks["mcp"] = {"ok": False, "error": "EUGENE_MCP_SERVER_URL not set"}
        overall_ok = False

    # 3. JWT signing secret configured
    secret_configured = bool(os.environ.get("EUGENE_CLIENT_SECRET"))
    checks["jwt_secret"] = {"ok": secret_configured}
    overall_ok &= secret_configured

    if not overall_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "OK" if overall_ok else "DEGRADED",
        "service": "eugene-agent-ws",
        "checks": checks,
    }
