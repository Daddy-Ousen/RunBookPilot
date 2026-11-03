"""Tests for the 5 Meta AI Developer Hackathon upgrades."""

from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi.testclient import TestClient

from app.llm import LLMConfig
from app.main import create_app


SAMPLE_PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _valid_triage_json() -> dict[str, Any]:
    return {
        "likely_cause": "TermService is stopped on srv-rds-01.corp.example.test blocking port 3389.",
        "confidence": "high",
        "matched_runbooks": ["rb-13-rdp-connection-refused"],
        "steps": [
            "Verify TermService status and listener on port 3389.",
            "Start TermService after technician approval.",
        ],
        "commands": [
            {
                "command": "Get-Service -Name TermService, UmRdpService",
                "purpose": "Check Remote Desktop services status",
                "risk": "read_only",
            },
            {
                "command": "Start-Service -Name TermService",
                "purpose": "Start Remote Desktop service",
                "risk": "read_only",  # intentionally wrong to verify X-Safety-Overrides header
            },
        ],
        "escalate": False,
        "escalate_reason": None,
    }


def _valid_runbook_draft_json() -> dict[str, Any]:
    return {
        "id": "rb-19-voip-vlan-bootloop",
        "title": "SIP VoIP Handset TFTP Bootloop and Voice VLAN 120 Failure",
        "tags": ["voip", "sip", "tftp", "vlan", "lldp", "poe"],
        "symptoms": [
            "Desk SIP VoIP handset on PoE switch port Gi1/0/24 is stuck in a TFTP firmware bootloop.",
            "Handset fails LLDP-MED voice VLAN 120 negotiation.",
        ],
        "checks": [
            {
                "command": "Get-NetAdapterAdvancedProperty -Name 'Ethernet'",
                "purpose": "Inspect local NIC VLAN and LLDP properties",
                "risk": "read_only",
            },
            {
                "command": "Test-NetConnection -ComputerName 10.20.120.10 -Port 69",
                "purpose": "Check reachability to TFTP provisioning server",
                "risk": "read_only",
            },
        ],
        "fixes": [
            {
                "command": "Restart-Service -Name DhcpServer -Force",
                "purpose": "Restart DHCP scope serving Option 150 TFTP server address",
                "risk": "read_only",  # intentionally wrong to verify server-side override to needs_approval
            }
        ],
        "escalation_rule": "Escalate to network engineering if PoE switch port Gi1/0/24 hardware fault persists.",
    }


def test_multimodal_screenshot_triage_and_telemetry_headers() -> None:
    captured_requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(_valid_triage_json())}}]},
        )

    cfg = LLMConfig(
        base_url="https://api.meta.ai/v1",
        model="muse-spark-1.3",
        api_key="test-meta-key",
    )
    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = TestClient(create_app(llm_config=cfg, llm_http_client=mock_http))

    resp = client.post(
        "/triage",
        json={
            "ticket": "Users cannot connect to srv-rds-01.corp.example.test. See attached screenshot.",
            "screenshot_data_url": SAMPLE_PNG_DATA_URL,
            "screenshot_caption": "Remote Desktop Connection port 3389 TermService stopped fDenyTSConnections",
            "reasoning_mode": "deep",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["matched_runbooks"] == ["rb-13-rdp-connection-refused"]
    # Verify deterministic safety override upgraded Start-Service to needs_approval
    assert body["commands"][1]["risk"] == "needs_approval"

    # Verify telemetry headers
    assert resp.headers.get("X-Meta-Model") == "muse-spark-1.3"
    assert resp.headers.get("X-Reasoning-Mode") == "deep"
    assert resp.headers.get("X-Safety-Overrides") == "1"
    bm25_scores = json.loads(resp.headers.get("X-BM25-Scores", "{}"))
    assert "rb-13-rdp-connection-refused" in bm25_scores

    # Verify multimodal payload sent to Meta Muse Spark
    assert len(captured_requests) == 1
    user_msg = captured_requests[0]["messages"][1]
    assert isinstance(user_msg["content"], list)
    assert user_msg["content"][0]["type"] == "text"
    assert "REASONING MODE: Deep multi-hop verification enabled." in user_msg["content"][0]["text"]
    assert "<SCREENSHOT_VISUAL_CONTEXT>" in user_msg["content"][0]["text"]
    assert user_msg["content"][1]["type"] == "image_url"
    assert user_msg["content"][1]["image_url"]["url"] == SAMPLE_PNG_DATA_URL


def test_rejects_invalid_screenshot_data_url_prefix() -> None:
    cfg = LLMConfig(
        base_url="https://api.meta.ai/v1",
        model="muse-spark-1.3",
        api_key="test-meta-key",
    )
    client = TestClient(create_app(llm_config=cfg))
    resp = client.post(
        "/triage",
        json={
            "ticket": "Broken RDP",
            "screenshot_data_url": "https://evil.example.test/payload.png",
        },
    )
    assert resp.status_code == 422


def test_closed_loop_rmm_diagnostic_retriage() -> None:
    captured_prompt = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_prompt
        payload = json.loads(request.content)
        captured_prompt = payload["messages"][1]["content"]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(_valid_triage_json())}}]},
        )

    cfg = LLMConfig(
        base_url="https://api.meta.ai/v1",
        model="muse-spark-1.3",
        api_key="test-meta-key",
    )
    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = TestClient(create_app(llm_config=cfg, llm_http_client=mock_http))

    rmm_output = (
        "[NinjaOne RMM STAGED SIMULATION - NOT EXECUTED ON HOST]\n"
        "Target Endpoint : srv-rds-01.corp.example.test\n"
        "Status   Name               DisplayName\n"
        "Stopped  TermService        Remote Desktop Services"
    )
    resp = client.post(
        "/triage",
        json={
            "ticket": "Cannot RDP to srv-rds-01.corp.example.test on port 3389.",
            "rmm_diagnostic_output": rmm_output,
            "reasoning_mode": "standard",
        },
    )
    assert resp.status_code == 200
    assert "<RMM_DIAGNOSTIC_OUTPUT>" in captured_prompt
    assert "Stopped  TermService" in captured_prompt


def test_autonomous_runbook_draft_and_hot_index_into_bm25() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(_valid_runbook_draft_json())}}]},
        )

    cfg = LLMConfig(
        base_url="https://api.meta.ai/v1",
        model="muse-spark-1.3",
        api_key="test-meta-key",
    )
    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = TestClient(create_app(llm_config=cfg, llm_http_client=mock_http))

    # Initially 18 runbooks
    health_before = client.get("/health").json()
    assert health_before["runbooks_loaded"] == 18

    # Step 1: Draft a new runbook for an uncovered VoIP ticket
    voip_ticket = (
        "Desk SIP VoIP handset on PoE switch port Gi1/0/24 is stuck in a TFTP firmware "
        "bootloop and failing LLDP-MED voice VLAN 120 negotiation."
    )
    draft_resp = client.post(
        "/runbooks/draft",
        json={
            "ticket": voip_ticket,
            "escalate_reason": "No VoIP/SIP runbook in corpus.",
        },
    )
    assert draft_resp.status_code == 200
    draft_data = draft_resp.json()
    assert draft_data["id"] == "rb-19-voip-vlan-bootloop"
    # Verify deterministic safety classifier upgraded Restart-Service to needs_approval
    assert draft_data["fixes"][0]["risk"] == "needs_approval"
    assert "## Checks" in draft_data["markdown"]
    assert "## Fixes" in draft_data["markdown"]

    # Step 2: Hot-index the synthesized Markdown runbook into the session BM25 index
    index_resp = client.post("/runbooks/index", json={"markdown": draft_data["markdown"]})
    assert index_resp.status_code == 200
    index_data = index_resp.json()
    assert index_data["id"] == "rb-19-voip-vlan-bootloop"
    assert index_data["total_runbooks_indexed"] == 19

    # Step 3: Verify /health and /runbooks now include the 19th runbook
    health_after = client.get("/health").json()
    assert health_after["runbooks_loaded"] == 19
    runbook_ids = [r["id"] for r in client.get("/runbooks").json()]
    assert "rb-19-voip-vlan-bootloop" in runbook_ids


def test_safety_inspect_and_eval_summary_endpoints() -> None:
    client = TestClient(create_app())

    # Safe read-only command
    ro_resp = client.post(
        "/safety/inspect",
        json={"command": "Get-ADUser -Identity user01 -Properties LockedOut, BadPwdCount"},
    )
    assert ro_resp.status_code == 200
    ro_data = ro_resp.json()
    assert ro_data["risk"] == "read_only"
    assert ro_data["executed_on_host"] is False
    assert len(ro_data["stages"]) == 1

    # Adversarial semicolon chain
    adv_resp = client.post(
        "/safety/inspect",
        json={"command": "Get-Service Spooler; Stop-Service Spooler -Force"},
    )
    assert adv_resp.status_code == 200
    adv_data = adv_resp.json()
    assert adv_data["risk"] == "needs_approval"
    assert ";" in adv_data["reason"]

    # Live 20-ticket BM25 evaluation summary
    eval_resp = client.get("/eval/summary")
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["total_tickets"] == 20
    assert eval_data["covered_tickets"] == 17
    assert eval_data["escalation_tickets"] == 3
    assert eval_data["bm25_top3_hits"] == 17
    assert eval_data["bm25_top3_hit_rate"] == 100.0
    assert eval_data["mislabeled_needs_approval"] == 0
    assert len(eval_data["rows"]) == 20


def test_ui_renders_all_five_hackathon_upgrade_controls() -> None:
    client = TestClient(create_app())
    html = client.get("/").text
    for expected_id in (
        'id="nav-tab-eval"',
        'id="eval-workspace"',
        'id="reasoning-mode-select"',
        'id="screenshot-file-input"',
        'id="btn-sample-shot-rdp"',
        'id="btn-sample-shot-vss"',
        'id="rmm-loop-bar"',
        'id="btn-draft-runbook"',
        'id="btn-hot-index-runbook"',
        'id="safety-inspect-form"',
    ):
        assert expected_id in html, f"Missing expected UI element {expected_id}"
