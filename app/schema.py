"""Pydantic v2 schemas for RunbookPilot triage requests and responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ConfidenceLevel = Literal["low", "medium", "high"]
CommandRisk = Literal["read_only", "needs_approval"]

MAX_TICKET_CHARS = 4000


class CommandItem(BaseModel):
    """A suggested PowerShell command with purpose and risk classification."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    command: str = Field(..., min_length=1, description="PowerShell command to display (never executed).")
    purpose: str = Field(..., min_length=1, description="What this command checks or changes.")
    risk: CommandRisk = Field(..., description="Deterministic risk label: read_only or needs_approval.")


class TriageResult(BaseModel):
    """Structured diagnosis and remediation plan grounded in matched runbooks."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    likely_cause: str = Field(..., min_length=1, description="Root-cause summary grounded in runbooks.")
    confidence: ConfidenceLevel = Field(..., description="Confidence level: low, medium, or high.")
    matched_runbooks: list[str] = Field(..., description="List of matched runbook IDs.")
    steps: list[str] = Field(..., description="Ordered diagnostic and remediation steps.")
    commands: list[CommandItem] = Field(..., description="PowerShell commands associated with the plan.")
    escalate: bool = Field(..., description="True when ticket must be escalated or is uncovered by runbooks.")
    escalate_reason: str | None = Field(
        default=None,
        description="Reason for escalation when escalate is True, otherwise null.",
    )

    @field_validator("escalate_reason", mode="before")
    @classmethod
    def _normalize_empty_escalate_reason(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("matched_runbooks", "steps")
    @classmethod
    def _reject_blank_items(cls, items: list[str]) -> list[str]:
        cleaned = [item.strip() for item in items if item.strip()]
        if len(cleaned) != len(items):
            raise ValueError("List items must not be empty strings.")
        return cleaned

    @model_validator(mode="after")
    def _validate_escalation_consistency(self) -> TriageResult:
        if self.escalate and not self.escalate_reason:
            raise ValueError("escalate_reason must be provided when escalate is True.")
        return self


class TriageRequest(BaseModel):
    """Incoming support ticket payload for POST /triage."""

    model_config = ConfigDict(extra="forbid")

    ticket: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TICKET_CHARS,
        description="Support ticket text (max 4000 characters).",
    )

    @field_validator("ticket", mode="before")
    @classmethod
    def _validate_raw_length_and_strip(cls, value: object) -> object:
        if not isinstance(value, str):
            raise ValueError("ticket must be a string.")
        if len(value) > MAX_TICKET_CHARS:
            raise ValueError(f"ticket exceeds maximum length of {MAX_TICKET_CHARS} characters.")
        stripped = value.strip()
        if not stripped:
            raise ValueError("ticket must not be empty or whitespace only.")
        return stripped
