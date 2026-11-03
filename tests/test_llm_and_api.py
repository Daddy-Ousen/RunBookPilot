"""Tests for Meta-only LLM client, bad-JSON retry, timeout, and FastAPI endpoints."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.llm import (
    LLMConfig,
    LLMConfigError,
    LLMResponseError,
    LLMTimeoutError,
    generate_triage,
    load_llm_config,
)
from app.main import create_app
from app.retrieval import Runbook, ScoredRunbook


def _sample_scored_runbook() -> ScoredRunbook:
    return ScoredRunbook(
        runbook=Runbook(
            id="rb-07-dns-resolution-failure",
            title="Internal or External DNS Resolution Failure",
            tags=["dns", "nslookup"],
            body="## Symptoms\nDNS lookup fails.\n## Checks\n- `ipconfig /all`\n## Fixes\n- `Clear-DnsClientCache`",
            path=Path("07_dns_resolution_failure.md"),
        ),
        score=12.5,
    )


def _valid_triage_payload() -> dict[str, object]:
    return {
        "likely_cause": "Stale local DNS resolver cache preventing internal FQDN lookup.",
        "confidence": "high",
        "matched_runbooks": ["rb-07-dns-resolution-failure"],
        "steps": ["Inspect configured DNS servers", "Flush local DNS resolver cache"],
        "commands": [
            {"command": "ipconfig /all", "purpose": "Check DNS servers", "risk": "read_only"},
            {
                "command": "Clear-DnsClientCache",
                "purpose": "Clear stale DNS cache",
                "risk": "read_only",  # intentionally wrong to verify safety override in API
            },
        ],
        "escalate": False,
        "escalate_reason": None,
    }


@pytest.mark.parametrize(
    "forbidden_model",
    [
        "gemini-2.5-pro",
        "google/gemini-2.0-flash",
        "gpt-4o",
        "claude-3-5-sonnet",
        "mistral-large-latest",
        "qwen-2.5-72b-instruct",
        "deepseek-r1",
    ],
)
def test_load_llm_config_rejects_non_meta_models(
    monkeypatch: pytest.MonkeyPatch, forbidden_model: str
) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://api.example.test/v1")
    monkeypatch.setenv("LLM_MODEL", forbidden_model)
    monkeypatch.setenv("LLM_API_KEY", "test-secret-key")

    with pytest.raises(LLMConfigError):
        load_llm_config()


@pytest.mark.parametrize(
    "meta_model",
    [
        "muse-spark-1.3",
        "muse-spark-1.3-contributor",
        "muse-wonder-1.0",
        "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "llama-3.3-70b-versatile",
    ],
)
def test_load_llm_config_accepts_meta_muse_and_llama_and_hides_key(
    monkeypatch: pytest.MonkeyPatch, meta_model: str
) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://api.meta.ai/v1")
    monkeypatch.setenv("LLM_MODEL", meta_model)
    monkeypatch.setenv("LLM_API_KEY", "super-secret-token-value")

    cfg = load_llm_config()
    assert cfg.model == meta_model
    assert "super-secret-token-value" not in repr(cfg)


def test_generate_triage_omits_temperature_for_muse_spark_models() -> None:
    captured_body: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_body
        captured_body = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(_valid_triage_payload())}}]},
        )

    cfg = LLMConfig(
        base_url="https://api.meta.ai/v1",
        model="muse-spark-1.3",
        api_key="test-key",
    )

    async def _run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await generate_triage(
                "Workstation cannot resolve internal DNS name",
                [_sample_scored_runbook()],
                request_id="req-muse",
                config=cfg,
                http_client=client,
            )
            assert result.matched_runbooks == ["rb-07-dns-resolution-failure"]
            assert captured_body["model"] == "muse-spark-1.3"
            assert "temperature" not in captured_body

    asyncio.run(_run())


def test_generate_triage_retries_once_on_bad_json_and_succeeds() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "{not valid json!!!"}}]},
            )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(_valid_triage_payload())}}]},
        )

    cfg = LLMConfig(
        base_url="https://api.example.test/v1",
        model="meta-llama/Llama-3.3-70B-Instruct",
        api_key="test-key",
    )

    async def _run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await generate_triage(
                "Workstation cannot resolve internal DNS name",
                [_sample_scored_runbook()],
                request_id="req-retry-ok",
                config=cfg,
                http_client=client,
            )
            assert result.matched_runbooks == ["rb-07-dns-resolution-failure"]
            assert attempts == 2

    asyncio.run(_run())


def test_generate_triage_fails_after_single_retry_on_persistent_bad_json() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{\"likely_cause\": \"incomplete\"}"}}]},
        )

    cfg = LLMConfig(
        base_url="https://api.example.test/v1",
        model="meta-llama/Llama-3.3-70B-Instruct",
        api_key="test-key",
    )

    async def _run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(LLMResponseError):
                await generate_triage(
                    "DNS lookup broken",
                    [_sample_scored_runbook()],
                    request_id="req-retry-fail",
                    config=cfg,
                    http_client=client,
                )
            assert attempts == 2

    asyncio.run(_run())


def test_generate_triage_raises_timeout_error() -> None:
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Simulated upstream timeout", request=request)

    cfg = LLMConfig(
        base_url="https://api.example.test/v1",
        model="meta-llama/Llama-3.3-70B-Instruct",
        api_key="test-key",
        timeout_seconds=5.0,
    )

    async def _run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(timeout_handler)) as client:
            with pytest.raises(LLMTimeoutError):
                await generate_triage(
                    "DNS lookup broken",
                    [_sample_scored_runbook()],
                    request_id="req-timeout",
                    config=cfg,
                    http_client=client,
                )

    asyncio.run(_run())


def test_fastapi_endpoints_safety_override_size_limit_rate_limit_and_log_privacy(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(_valid_triage_payload())}}]},
        )

    cfg = LLMConfig(
        base_url="https://api.example.test/v1",
        model="meta-llama/Llama-3.3-70B-Instruct",
        api_key="secret-api-key-never-log",
    )
    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    test_app = create_app(
        rate_limit_requests=2,
        rate_limit_window_seconds=60.0,
        llm_config=cfg,
        llm_http_client=mock_http,
    )

    unique_ticket_marker = "UNIQUE_SENSITIVE_TICKET_TOKEN_99481"

    with caplog.at_level(logging.INFO):
        with TestClient(test_app) as client:
            health = client.get("/health")
            assert health.status_code == 200
            assert health.json() == {"status": "ok", "runbooks_loaded": 18}

            oversized = client.post("/triage", json={"ticket": "x" * 4001})
            assert oversized.status_code == 422

            ok1 = client.post(
                "/triage",
                json={"ticket": f"Cannot resolve srv-file-01 via DNS ({unique_ticket_marker})"},
            )
            assert ok1.status_code == 200
            data = ok1.json()
            assert data["commands"][0]["risk"] == "read_only"
            # Model returned read_only for Clear-DnsClientCache; API must override to needs_approval
            assert data["commands"][1]["risk"] == "needs_approval"

            ok2 = client.post("/triage", json={"ticket": "Second DNS ticket within quota"})
            assert ok2.status_code == 200

            limited = client.post("/triage", json={"ticket": "Third request exceeds rate limit"})
            assert limited.status_code == 429
            assert "Retry-After" in limited.headers

    logged_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "request_id=" in logged_text
    assert unique_ticket_marker not in logged_text
    assert "secret-api-key-never-log" not in logged_text


def test_vercel_forwarded_ip_rate_limiting_and_ui_elements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VERCEL", "1")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(_valid_triage_payload())}}]},
        )

    cfg = LLMConfig(
        base_url="https://api.meta.ai/v1",
        model="muse-spark-1.3",
        api_key="test-key",
    )
    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    test_app = create_app(
        rate_limit_requests=1,
        rate_limit_window_seconds=60.0,
        llm_config=cfg,
        llm_http_client=mock_http,
    )

    with TestClient(test_app) as client:
        ui = client.get("/")
        assert ui.status_code == 200
        for elem_id in (
            "ticket-input",
            "loading-state",
            "escalate-banner",
            "approval-warning-banner",
            "likely-cause-text",
            "confidence-badge",
            "matched-runbooks-list",
            "steps-list",
            "commands-list",
            "theme-toggle",
        ):
            assert elem_id in ui.text

        # Visitor A hits 1-request limit; Visitor B behind Vercel edge still succeeds
        r_a1 = client.post(
            "/triage",
            json={"ticket": "DNS issue A"},
            headers={"x-vercel-forwarded-for": "203.0.113.10"},
        )
        assert r_a1.status_code == 200

        r_a2 = client.post(
            "/triage",
            json={"ticket": "DNS issue A repeat"},
            headers={"x-vercel-forwarded-for": "203.0.113.10"},
        )
        assert r_a2.status_code == 429

        r_b1 = client.post(
            "/triage",
            json={"ticket": "DNS issue B"},
            headers={"x-vercel-forwarded-for": "198.51.100.42"},
        )
        assert r_b1.status_code == 200
