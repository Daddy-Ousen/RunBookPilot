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
        ):
            assert elem_id in ui.text
        assert len(PROVIDER_CATALOG) == 12
