"""Tests for RMM and Ticketing/PSA staged integrations registry, API endpoints, and privacy."""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from app.integrations import PROVIDER_CATALOG, SECRET_MASK
from app.main import create_app


def test_list_integrations_returns_all_12_popular_rmm_and_ticketing_providers() -> None:
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/integrations")
        assert resp.status_code == 200
        providers = resp.json()

    assert len(providers) == 12
    ticketing_ids = {p["id"] for p in providers if p["category"] == "ticketing"}
    rmm_ids = {p["id"] for p in providers if p["category"] == "rmm"}

    assert ticketing_ids == {
        "connectwise_psa",
        "autotask_psa",
        "halopsa",
        "servicenow_itsm",
        "jira_service_management",
        "freshservice",
    }
    assert rmm_ids == {
        "ninjaone_rmm",
        "datto_rmm",
        "connectwise_automate",
        "nable_ncentral",
        "atera_rmm",
        "syncro_msp",
    }

    for p in providers:
        assert p["remote_execution_allowed"] is False
        assert p["live_sync_active"] is False
        assert p["status"] == "not_configured"
        assert p["enabled"] is False
        assert p["webhook_path"] == f"/integrations/webhooks/{p['id']}"
        for f_spec in p["fields"]:
            if f_spec["field_type"] == "url":
                assert ".example.test" in f_spec["placeholder"]


def test_stage_update_secret_masking_and_secret_preservation_on_reupdate(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app()
    sensitive_secret = "CW_PRIVATE_SECRET_VALUE_9918273"

    with caplog.at_level(logging.INFO):
        with TestClient(app) as client:
            # 1. Save partial draft (enabled=False) -> status becomes 'paused', secret is masked
            draft_resp = client.put(
                "/integrations/connectwise_psa",
                json={
                    "enabled": False,
                    "sync_mode": "draft_internal_note",
                    "values": {
                        "site_url": "https://psa.msp-alpha.example.test",
                        "company_id": "msp_alpha",
                        "private_key": sensitive_secret,
                    },
                },
            )
            assert draft_resp.status_code == 200
            draft_data = draft_resp.json()
            assert draft_data["status"] == "paused"
            assert draft_data["configured_values"]["private_key"] == SECRET_MASK
            assert draft_data["has_saved_secrets"]["private_key"] is True
            assert sensitive_secret not in draft_resp.text

            # 2. Attempting to stage as ready (enabled=True) while client_id/public_key missing -> 422
            incomplete_stage = client.put(
                "/integrations/connectwise_psa",
                json={
                    "enabled": True,
                    "sync_mode": "webhook_auto_triage",
                    "values": {
                        "site_url": "https://psa.msp-alpha.example.test",
                        "company_id": "msp_alpha",
                        "private_key": SECRET_MASK,
                    },
                },
            )
            assert incomplete_stage.status_code == 422

            # 3. Complete remaining required fields while echoing SECRET_MASK -> preserves secret & stages
            staged_resp = client.put(
                "/integrations/connectwise_psa",
                json={
                    "enabled": True,
                    "sync_mode": "webhook_auto_triage",
                    "values": {
                        "site_url": "https://psa.msp-alpha.example.test",
                        "company_id": "msp_alpha",
                        "client_id": "00000000-0000-0000-0000-000000000000",
                        "public_key": "cw_pub_01",
                        "private_key": SECRET_MASK,
                        "service_board": "Tier 1 Helpdesk",
                    },
                },
            )
            assert staged_resp.status_code == 200
            staged_data = staged_resp.json()
            assert staged_data["status"] == "staged"
            assert staged_data["enabled"] is True
            assert staged_data["sync_mode"] == "webhook_auto_triage"
            assert staged_data["configured_values"]["private_key"] == SECRET_MASK
            assert staged_data["has_saved_secrets"]["private_key"] is True
            assert staged_data["updated_at"] is not None

            # 4. Dry-run test without body validates stored state (including preserved secret)
            test_resp = client.post("/integrations/connectwise_psa/test")
            assert test_resp.status_code == 200
            test_data = test_resp.json()
            assert test_data["ok"] is True
            assert test_data["status"] == "staged_ready"
            assert test_data["missing_fields"] == []
            assert test_data["invalid_fields"] == []

            # 5. Reset clears configuration back to not_configured
            reset_resp = client.delete("/integrations/connectwise_psa")
            assert reset_resp.status_code == 200
            reset_data = reset_resp.json()
            assert reset_data["status"] == "not_configured"
            assert reset_data["enabled"] is False
            assert reset_data["configured_values"]["private_key"] == ""
            assert reset_data["has_saved_secrets"]["private_key"] is False

    logged_text = "\n".join(record.getMessage() for record in caplog.records)
    assert sensitive_secret not in logged_text


def test_integration_url_and_unknown_field_validation() -> None:
    app = create_app()
    with TestClient(app) as client:
        bad_url = client.put(
            "/integrations/ninjaone_rmm",
            json={
                "enabled": False,
                "sync_mode": "draft_internal_note",
                "values": {
                    "region_url": "ftp://invalid-scheme.example.test",
                },
            },
        )
        assert bad_url.status_code == 422

        unknown_field = client.put(
            "/integrations/ninjaone_rmm",
            json={
                "enabled": False,
                "sync_mode": "draft_internal_note",
                "values": {
                    "non_existent_field": "value",
                },
            },
        )
        assert unknown_field.status_code == 422

        dry_run_fail = client.post(
            "/integrations/ninjaone_rmm/test",
            json={
                "values": {
                    "region_url": "not-a-valid-url",
                }
            },
        )
        assert dry_run_fail.status_code == 200
        body = dry_run_fail.json()
        assert body["ok"] is False
        assert body["status"] == "validation_failed"
        assert "region_url" in body["invalid_fields"]
        assert "client_id" in body["missing_fields"]
        assert "client_secret" in body["missing_fields"]


def test_webhook_standby_endpoint_acknowledges_and_never_logs_payload(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(rate_limit_requests=3, rate_limit_window_seconds=60.0)
    secret_ticket_marker = "WEBHOOK_SENSITIVE_TICKET_BODY_88271"

    with caplog.at_level(logging.INFO):
        with TestClient(app) as client:
            ack = client.post(
                "/integrations/webhooks/halopsa",
                json={
                    "event": "ticket.created",
                    "ticket_id": 4019,
                    "summary": f"User locked out ({secret_ticket_marker})",
                },
            )
            assert ack.status_code == 202
            ack_data = ack.json()
            assert ack_data["provider_id"] == "halopsa"
            assert ack_data["accepted"] is True
            assert ack_data["mode"] == "staged_standby"
            assert ack_data["provider_status"] == "not_configured"
            assert len(ack_data["request_id"]) > 0

            unknown_wh = client.post("/integrations/webhooks/unknown_rmm", json={"ping": True})
            assert unknown_wh.status_code == 404

            bad_json_wh = client.post(
                "/integrations/webhooks/halopsa",
                content=b"{malformed json",
                headers={"Content-Type": "application/json"},
            )
            assert bad_json_wh.status_code == 422

    logged_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "webhook_standby_ack=halopsa" in logged_text
    assert secret_ticket_marker not in logged_text


def test_ui_includes_integrations_settings_workspace_elements() -> None:
    app = create_app()
    with TestClient(app) as client:
        ui = client.get("/")
        assert ui.status_code == 200
        for elem_id in (
            "nav-tab-triage",
            "nav-tab-integrations",
            "integrations-workspace",
            "integration-provider-list",
            "integration-config-form",
            "cfg-fields-grid",
            "cfg-webhook-url",
            "cfg-test-btn",
            "cfg-save-btn",
            "pending-queue-panel",
            "pending-queue-list",
            "rmm-telemetry-panel",
            "psa-writeback-panel",
        ):
            assert elem_id in ui.text
        assert len(PROVIDER_CATALOG) == 12


def test_pending_queue_rmm_telemetry_and_staged_filter() -> None:
    app = create_app()
    with TestClient(app) as client:
        # 1. Default queue contains 6 seeded items with RMM device telemetry
        q_resp = client.get("/integrations/queue")
        assert q_resp.status_code == 200
        items = q_resp.json()
        assert len(items) == 6
        first = items[0]
        assert first["id"] == "INC-40821"
        assert first["device"] is not None
        assert first["device"]["hostname"] == "dc-01.corp.example.test"
        assert first["device"]["rmm_provider_id"] == "ninjaone_rmm"

        # 2. Staged-only filter returns empty before any connector is staged
        staged_empty = client.get("/integrations/queue?staged_only=true")
        assert staged_empty.status_code == 200
        assert staged_empty.json() == []

        # 3. Stage ConnectWise PSA and verify staged_only returns ConnectWise tickets
        stage_cw = client.put(
            "/integrations/connectwise_psa",
            json={
                "enabled": True,
                "sync_mode": "draft_internal_note",
                "values": {
                    "site_url": "https://psa.msp-alpha.example.test",
                    "company_id": "msp_alpha",
                    "client_id": "00000000-0000-0000-0000-000000000000",
                    "public_key": "pub_01",
                    "private_key": "prv_secret_01",
                },
            },
        )
        assert stage_cw.status_code == 200

        staged_items = client.get("/integrations/queue?staged_only=true").json()
        assert len(staged_items) == 1
        assert staged_items[0]["provider_id"] == "connectwise_psa"


def test_psa_ticket_writeback_and_escalation_updates_queue_status(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app()
    secret_cause_marker = "SENSITIVE_DIAGNOSIS_NOTE_CONTENT_77312"

    with caplog.at_level(logging.INFO):
        with TestClient(app) as client:
            wb = client.post(
                "/integrations/tickets/INC-40821/writeback",
                json={
                    "provider_id": "connectwise_psa",
                    "action": "internal_note",
                    "likely_cause": f"Stale cached credentials on workstation ({secret_cause_marker}).",
                    "confidence": "high",
                    "matched_runbooks": ["rb-01-ad-account-lockout"],
                    "steps": ["Check Event ID 4740 caller computer", "Clear cached credentials"],
                    "commands": [
                        {
                            "command": "Get-ADUser -Identity user01 -Properties LockedOut",
                            "purpose": "Check lockout state",
                            "risk": "read_only",
                        }
                    ],
                },
            )
            assert wb.status_code == 200
            wb_data = wb.json()
            assert wb_data["ticket_status"] == "triaged"
            assert wb_data["mode"] == "staged_simulation"
            assert "rb-01-ad-account-lockout" in wb_data["note_preview"]

            # Queue item status should now be 'triaged'
            queue_after = client.get("/integrations/queue").json()
            item_after = next(i for i in queue_after if i["id"] == "INC-40821")
            assert item_after["status"] == "triaged"

            # Escalation action transitions status to 'escalated'
            esc = client.post(
                "/integrations/tickets/INC-40821/writeback",
                json={
                    "provider_id": "connectwise_psa",
                    "action": "escalate",
                    "likely_cause": "Requires Tier 3 domain controller review.",
                    "confidence": "low",
                    "matched_runbooks": [],
                    "steps": [],
                    "commands": [],
                    "escalate_reason": "Domain controller replication conflict.",
                },
            )
            assert esc.status_code == 200
            assert esc.json()["ticket_status"] == "escalated"

    logged_text = "\n".join(record.getMessage() for record in caplog.records)
    assert secret_cause_marker not in logged_text


def test_safety_gated_rmm_command_dispatch_enforces_approval_for_mutating_commands(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app()
    unique_cmd_marker = "SENSITIVE_POWERSHELL_ARG_55192"

    with caplog.at_level(logging.INFO):
        with TestClient(app) as client:
            # 1. read_only command succeeds without technician approval
            ro_resp = client.post(
                "/integrations/rmm/dispatch",
                json={
                    "rmm_provider_id": "ninjaone_rmm",
                    "hostname": "dc-01.corp.example.test",
                    "command": f"Get-ADUser -Identity {unique_cmd_marker} -Properties LockedOut",
                    "purpose": "Verify lockout status",
                    "ticket_id": "INC-40821",
                    "approved_by_technician": False,
                },
            )
            assert ro_resp.status_code == 200
            ro_job = ro_resp.json()
            assert ro_job["classified_risk"] == "read_only"
            assert ro_job["executed_on_host"] is False
            assert ro_job["mode"] == "staged_simulation"

            # 2. needs_approval command WITHOUT technician approval is blocked (422)
            blocked_resp = client.post(
                "/integrations/rmm/dispatch",
                json={
                    "rmm_provider_id": "ninjaone_rmm",
                    "hostname": "dc-01.corp.example.test",
                    "command": "Unlock-ADAccount -Identity user01",
                    "purpose": "Unlock user01 AD account",
                    "ticket_id": "INC-40821",
                    "approved_by_technician": False,
                },
            )
            assert blocked_resp.status_code == 422

            # 3. needs_approval command WITH technician approval and approval_note succeeds
            approved_resp = client.post(
                "/integrations/rmm/dispatch",
                json={
                    "rmm_provider_id": "ninjaone_rmm",
                    "hostname": "dc-01.corp.example.test",
                    "command": "Unlock-ADAccount -Identity user01",
                    "purpose": "Unlock user01 AD account",
                    "ticket_id": "INC-40821",
                    "approved_by_technician": True,
                    "approval_note": "CHG-1042 approved by Tier 2 lead",
                },
            )
            assert approved_resp.status_code == 200
            app_job = approved_resp.json()
            assert app_job["classified_risk"] == "needs_approval"
            assert app_job["approved_by_technician"] is True
            assert app_job["executed_on_host"] is False

            # 4. Ticketing provider rejected for RMM dispatch
            wrong_cat = client.post(
                "/integrations/rmm/dispatch",
                json={
                    "rmm_provider_id": "connectwise_psa",
                    "hostname": "dc-01.corp.example.test",
                    "command": "Get-Service -Name Spooler",
                    "purpose": "Check spooler",
                },
            )
            assert wrong_cat.status_code == 422

            # 5. Jobs list contains the 2 queued jobs
            jobs = client.get("/integrations/rmm/jobs").json()
            assert len(jobs) == 2

    logged_text = "\n".join(record.getMessage() for record in caplog.records)
    assert unique_cmd_marker not in logged_text
