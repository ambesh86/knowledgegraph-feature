"""API authentication and request correlation.

The scanner shipped with no authentication at all while publishing its port on
`0.0.0.0`. A production-readiness audit demonstrated the consequence by rewriting
`notify_min_score` from an unauthenticated curl against the running container — the
same request could have triggered scans until the USPTO quota was exhausted, or
dismissed every signal on the Radar.

These tests are the regression barrier for that. The most important one is
`test_a_new_endpoint_is_protected_by_default`: auth is applied as an app-level
dependency precisely so that adding a route cannot silently open a hole, and that
property is worth asserting rather than trusting.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from scout.security import _OPEN_PATHS, auth_enabled, auth_status, configured_token


@pytest.fixture
def secured(store, monkeypatch):
    """A client with authentication switched on."""
    from scout import api

    monkeypatch.setenv("SCOUT_API_TOKEN", "s3cr3t-token")
    monkeypatch.setattr(api, "store", store)
    monkeypatch.setattr(api.index, "_store", store)
    monkeypatch.setattr(api.orchestrator, "store", store)
    monkeypatch.setattr(api.index, "_areas", {})
    with TestClient(api.app) as c:
        yield c
    api.index._areas = {}


@pytest.fixture
def unsecured(store, monkeypatch):
    from scout import api

    monkeypatch.delenv("SCOUT_API_TOKEN", raising=False)
    monkeypatch.setattr(api, "store", store)
    monkeypatch.setattr(api.index, "_store", store)
    monkeypatch.setattr(api.orchestrator, "store", store)
    monkeypatch.setattr(api.index, "_areas", {})
    with TestClient(api.app) as c:
        yield c
    api.index._areas = {}


AUTH = {"Authorization": "Bearer s3cr3t-token"}


class TestTokenEnforcement:
    def test_health_stays_open(self, secured):
        """Docker's healthcheck runs before any secret is available, and /health
        exposes nothing beyond liveness."""
        assert secured.get("/health").status_code == 200

    @pytest.mark.parametrize(
        "path", ["/signals", "/companies", "/stats", "/runs", "/config", "/areas", "/freshness"]
    )
    def test_reads_require_a_token(self, secured, path):
        assert secured.get(path).status_code == 401

    def test_config_writes_require_a_token(self, secured):
        """REGRESSION: this exact request succeeded against the live container."""
        assert secured.put("/config", json={"notify_min_score": 99}).status_code == 401

    def test_scan_trigger_requires_a_token(self, secured):
        """An open scan trigger is a way to exhaust a rate-limited USPTO quota."""
        assert secured.post("/scan", json={}).status_code == 401

    def test_a_valid_token_is_accepted(self, secured):
        assert secured.get("/signals", headers=AUTH).status_code == 200

    def test_the_alternate_header_works(self, secured):
        assert secured.get("/signals", headers={"X-Scout-Token": "s3cr3t-token"}).status_code == 200

    @pytest.mark.parametrize(
        "header",
        [
            {"Authorization": "Bearer wrong"},
            {"Authorization": "Basic s3cr3t-token"},
            {"Authorization": "s3cr3t-token"},
            {"X-Scout-Token": "wrong"},
            {"X-Scout-Token": ""},
            {"Authorization": "Bearer "},
            {"Authorization": "Bearer S3CR3T-TOKEN"},
        ],
    )
    def test_malformed_or_wrong_tokens_are_rejected(self, secured, header):
        assert secured.get("/signals", headers=header).status_code == 401

    def test_surrounding_whitespace_is_tolerated(self, secured):
        """Env files and copy-paste routinely add a trailing newline or space, and an
        attacker who knows "token + space" already knows the token. Rejecting it buys
        nothing and costs a genuinely confusing outage."""
        assert secured.get("/signals", headers={"Authorization": "Bearer s3cr3t-token "}).status_code == 200

    def test_rejection_does_not_leak_why(self, secured):
        """A specific message is a hint to whoever is guessing."""
        body = secured.get("/signals", headers={"Authorization": "Bearer wrong"}).json()
        assert body["detail"] == "Missing or invalid API token"
        assert "s3cr3t" not in str(body)

    def test_a_new_endpoint_is_protected_by_default(self, secured):
        """Auth is an app-level dependency, so a route added later inherits it.

        This is the property that matters most: per-route decorators are the design
        where somebody eventually forgets one.
        """
        from scout import api

        # Docs routes are excluded because FastAPI mounts them outside the dependency
        # chain and their presence is decided at import time from the environment —
        # which in a container is set before the process starts, but in a test is
        # monkeypatched after. `docs_enabled()` is unit-tested separately below.
        docs = {"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}
        paths = {r.path for r in api.app.routes if hasattr(r, "path")}
        unprotected = {p for p in paths if p not in _OPEN_PATHS and p not in docs}

        for path in sorted(unprotected):
            if "{" in path:  # parameterised routes need a value; covered elsewhere
                continue
            assert secured.get(path).status_code in (401, 405), f"{path} was reachable"


class TestDocsExposure:
    """An authenticated deployment must not publish its full API surface.

    FastAPI mounts /docs, /redoc and /openapi.json bypassing app-level dependencies,
    so they cannot be token-protected — they are switched off instead. The schema
    holds no signal data, but it is free reconnaissance.
    """

    def test_docs_are_off_when_auth_is_on(self, monkeypatch):
        from scout.security import docs_enabled

        monkeypatch.setenv("SCOUT_API_TOKEN", "x")
        monkeypatch.delenv("SCOUT_ENABLE_DOCS", raising=False)
        assert docs_enabled() is False

    def test_docs_are_on_for_an_unauthenticated_local_run(self, monkeypatch):
        from scout.security import docs_enabled

        monkeypatch.delenv("SCOUT_API_TOKEN", raising=False)
        monkeypatch.delenv("SCOUT_ENABLE_DOCS", raising=False)
        assert docs_enabled() is True

    def test_docs_can_be_re_enabled_deliberately(self, monkeypatch):
        """For a deployment that wants them behind its own network controls."""
        from scout.security import docs_enabled

        monkeypatch.setenv("SCOUT_API_TOKEN", "x")
        monkeypatch.setenv("SCOUT_ENABLE_DOCS", "true")
        assert docs_enabled() is True


class TestUnauthenticatedMode:
    def test_service_still_serves_when_no_token_is_configured(self, unsecured):
        """Failing closed would break every local run and the whole test suite, and a
        service that refuses to boot without a secret grows a hard-coded default."""
        assert unsecured.get("/signals").status_code == 200

    def test_the_unauthenticated_state_is_visible_not_silent(self, unsecured):
        """Reported by /health and /status so it is apparent to whoever is looking at
        the deployment, not only to whoever reads the env file."""
        assert unsecured.get("/health").json()["auth"] == "disabled"
        assert unsecured.get("/status").json()["auth"] == "disabled"

    def test_helpers_agree(self, monkeypatch):
        monkeypatch.delenv("SCOUT_API_TOKEN", raising=False)
        assert auth_enabled() is False
        assert auth_status() == "disabled"
        assert configured_token() is None

        monkeypatch.setenv("SCOUT_API_TOKEN", "x")
        assert auth_enabled() is True
        assert auth_status() == "enabled"

    def test_whitespace_only_token_counts_as_unset(self, monkeypatch):
        """`SCOUT_API_TOKEN=" "` in an env file must not read as "authenticated"."""
        monkeypatch.setenv("SCOUT_API_TOKEN", "   ")
        assert configured_token() is None
        assert auth_enabled() is False


class TestRequestCorrelation:
    def test_a_request_id_is_returned(self, unsecured):
        assert unsecured.get("/health").headers.get("X-Request-Id")

    def test_an_inbound_request_id_is_preserved(self, unsecured):
        """A proxy that already assigns ids should keep owning them, so one id spans
        the whole hop chain."""
        res = unsecured.get("/health", headers={"X-Request-Id": "trace-abc-123"})
        assert res.headers["X-Request-Id"] == "trace-abc-123"

    def test_ids_differ_between_requests(self, unsecured):
        a = unsecured.get("/health").headers["X-Request-Id"]
        b = unsecured.get("/health").headers["X-Request-Id"]
        assert a != b


class TestS3CredentialScoping:
    """The scanner should authenticate to S3 as its own least-privilege identity.

    The shared `difflabs-website-deployment` key it used can also read the CSL
    lakehouse and the neo4j bucket — verified from inside the running container. A
    leak from a service that only reads four public APIs should not expose those.

    Precedence lives in code rather than docker-compose because compose gets it
    wrong: `environment:` overrides `env_file:`, and `${SCOUT_AWS_*}` substitutes from
    the shell, which never sees docker.env. Mapping it there rendered empty strings
    and would have blanked the credentials outright — caught by inspecting the
    rendered config before deploying.
    """

    def test_scoped_credentials_are_used_when_configured(self, monkeypatch):
        from scout.config import s3_credentials, s3_identity_source

        monkeypatch.setenv("SCOUT_AWS_ACCESS_KEY_ID", "AKIASCOPED")
        monkeypatch.setenv("SCOUT_AWS_SECRET_ACCESS_KEY", "shhh")
        assert s3_credentials() == {
            "aws_access_key_id": "AKIASCOPED",
            "aws_secret_access_key": "shhh",
        }
        assert s3_identity_source() == "scoped"

    def test_falls_back_to_the_default_chain(self, monkeypatch):
        """Unset must leave boto3 to its own chain — the shared key today, an
        instance or task role on AWS, with no code change."""
        from scout.config import s3_credentials, s3_identity_source

        monkeypatch.delenv("SCOUT_AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("SCOUT_AWS_SECRET_ACCESS_KEY", raising=False)
        assert s3_credentials() == {}
        assert s3_identity_source() == "default-chain"

    def test_half_configured_credentials_do_not_take_effect(self, monkeypatch):
        """An id without a secret is a typo, not a credential. Passing it to boto3
        would fail confusingly at the first S3 call rather than at startup."""
        from scout.config import s3_credentials

        monkeypatch.setenv("SCOUT_AWS_ACCESS_KEY_ID", "AKIASCOPED")
        monkeypatch.delenv("SCOUT_AWS_SECRET_ACCESS_KEY", raising=False)
        assert s3_credentials() == {}

    def test_whitespace_only_values_are_ignored(self, monkeypatch):
        from scout.config import s3_credentials

        monkeypatch.setenv("SCOUT_AWS_ACCESS_KEY_ID", "  ")
        monkeypatch.setenv("SCOUT_AWS_SECRET_ACCESS_KEY", "  ")
        assert s3_credentials() == {}

    def test_health_reports_which_identity_is_in_use(self, unsecured, monkeypatch):
        body = unsecured.get("/health").json()
        assert body["s3"]["identity"] in ("scoped", "default-chain")
