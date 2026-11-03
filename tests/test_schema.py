"""Tests for Pydantic v2 models in app/schema.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schema import MAX_TICKET_CHARS, CommandItem, TriageRequest, TriageResult


def test_valid_triage_result_non_escalated() -> None:
    result = TriageResult(
        likely_cause="Stale saved credentials locking AD user account.",
        confidence="high",
        matched_runbooks=["rb-02-ad-account-locked"],
        steps=["Check AD lockout properties", "Unlock account after verification"],
        commands=[
            CommandItem(
                command="Get-ADUser -Identity user01 -Properties LockedOut",
                purpose="Check lockout flag",
                risk="read_only",
            ),
            CommandItem(
                command="Unlock-ADAccount -Identity user01",
                purpose="Unlock AD account",
                risk="needs_approval",
            ),
        ],
        escalate=False,
        escalate_reason="",
    )
    assert result.confidence == "high"
    assert result.escalate is False
    assert result.escalate_reason is None


def test_valid_triage_result_escalated() -> None:
    result = TriageResult(
        likely_cause="No available Windows/M365 runbook covers macOS FileVault boot failure.",
        confidence="low",
        matched_runbooks=[],
        steps=["Escalate to Tier 2 Apple/Mac Engineering."],
        commands=[],
        escalate=True,
        escalate_reason="Out of runbook scope (macOS FileVault).",
    )
    assert result.escalate is True
    assert result.escalate_reason == "Out of runbook scope (macOS FileVault)."


def test_escalate_true_requires_escalate_reason() -> None:
    with pytest.raises(ValidationError):
        TriageResult(
            likely_cause="Uncovered ticket",
            confidence="low",
            matched_runbooks=[],
            steps=["Escalate"],
            commands=[],
            escalate=True,
            escalate_reason=None,
        )


def test_rejects_invalid_confidence_and_risk() -> None:
    with pytest.raises(ValidationError):
        TriageResult(
            likely_cause="DNS issue",
            confidence="certain",  # type: ignore[arg-type]
            matched_runbooks=["rb-07-dns-resolution-failure"],
            steps=["Check DNS"],
            commands=[],
            escalate=False,
            escalate_reason=None,
        )

    with pytest.raises(ValidationError):
        CommandItem(
            command="ipconfig /all",
            purpose="Inspect NIC",
            risk="safe",  # type: ignore[arg-type]
        )


def test_rejects_extra_fields_and_blank_items() -> None:
    with pytest.raises(ValidationError):
        TriageResult.model_validate(
            {
                "likely_cause": "DNS issue",
                "confidence": "medium",
                "matched_runbooks": ["rb-07-dns-resolution-failure"],
                "steps": ["Check DNS"],
                "commands": [],
                "escalate": False,
                "escalate_reason": None,
                "unexpected_field": "not allowed",
            }
        )

    with pytest.raises(ValidationError):
        TriageResult(
            likely_cause="DNS issue",
            confidence="medium",
            matched_runbooks=["rb-07-dns-resolution-failure"],
            steps=["   "],
            commands=[],
            escalate=False,
            escalate_reason=None,
        )


def test_triage_request_enforces_non_empty_and_4000_char_limit() -> None:
    exact = TriageRequest(ticket="a" * MAX_TICKET_CHARS)
    assert len(exact.ticket) == MAX_TICKET_CHARS

    with pytest.raises(ValidationError):
        TriageRequest(ticket="a" * (MAX_TICKET_CHARS + 1))

    # Padded whitespace pushing raw input over 4000 characters must also fail
    with pytest.raises(ValidationError):
        TriageRequest(ticket=(" " * 20) + ("a" * 3990))

    with pytest.raises(ValidationError):
        TriageRequest(ticket="   \n\t  ")
