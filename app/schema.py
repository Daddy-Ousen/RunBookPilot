"""Pydantic v2 schemas for RunbookPilot triage requests and responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ConfidenceLevel = Literal["low", "medium", "high"]
CommandRisk = Literal["read_only", "needs_approval"]
IntegrationCategory = Literal["ticketing", "rmm"]
IntegrationStatus = Literal["not_configured", "staged", "paused"]
IntegrationSyncMode = Literal["draft_internal_note", "webhook_auto_triage", "manual_pull"]
IntegrationFieldType = Literal["url", "text", "secret"]

MAX_TICKET_CHARS = 4000
MAX_INTEGRATION_FIELD_CHARS = 512


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


def _validate_integration_values_map(values: dict[str, str]) -> dict[str, str]:
    if len(values) > 24:
        raise ValueError("Too many integration configuration fields submitted.")
    cleaned: dict[str, str] = {}
    for raw_key, raw_val in values.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            raise ValueError("Field key must be a non-empty string.")
        if not isinstance(raw_val, str):
            raise ValueError(f"Field '{raw_key}' value must be a string.")
        if len(raw_val) > MAX_INTEGRATION_FIELD_CHARS:
            raise ValueError(
                f"Field '{raw_key}' exceeds maximum length of {MAX_INTEGRATION_FIELD_CHARS} characters."
            )
        cleaned[raw_key.strip()] = raw_val.strip()
    return cleaned


class IntegrationFieldSpec(BaseModel):
    """Schema descriptor for a single provider configuration field."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1)
    field_type: IntegrationFieldType
    placeholder: str = Field(..., min_length=1)
    required: bool = True
    help_text: str = Field(..., min_length=1)


class IntegrationProviderView(BaseModel):
    """Public masked representation of an RMM or Ticketing connector."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    category: IntegrationCategory
    protocol: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    capabilities: list[str]
    fields: list[IntegrationFieldSpec]
    webhook_path: str = Field(..., min_length=1)
    remote_execution_allowed: Literal[False] = False
    live_sync_active: Literal[False] = False
    status: IntegrationStatus
    enabled: bool
    sync_mode: IntegrationSyncMode
    configured_values: dict[str, str]
    has_saved_secrets: dict[str, bool]
    updated_at: str | None = None


class IntegrationUpdateRequest(BaseModel):
    """Payload for staging or updating a connector's settings."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    sync_mode: IntegrationSyncMode = "draft_internal_note"
    values: dict[str, str] = Field(default_factory=dict)

    @field_validator("values")
    @classmethod
    def _validate_values(cls, values: dict[str, str]) -> dict[str, str]:
        return _validate_integration_values_map(values)


class IntegrationTestRequest(BaseModel):
    """Optional draft values to validate during a staged dry-run check."""

    model_config = ConfigDict(extra="forbid")

    sync_mode: IntegrationSyncMode | None = None
    values: dict[str, str] | None = None

    @field_validator("values")
    @classmethod
    def _validate_optional_values(cls, values: dict[str, str] | None) -> dict[str, str] | None:
        if values is None:
            return None
        return _validate_integration_values_map(values)


class IntegrationTestResult(BaseModel):
    """Result of a staged dry-run validation check (no outbound live execution)."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    ok: bool
    status: Literal["staged_ready", "validation_failed"]
    mode: Literal["staged_dry_run"] = "staged_dry_run"
    message: str
    checked_fields: list[str]
    missing_fields: list[str]
    invalid_fields: list[str]


class WebhookAckResponse(BaseModel):
    """Standby acknowledgment returned by inbound PSA/RMM webhook receivers."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    accepted: bool = True
    mode: Literal["staged_standby"] = "staged_standby"
    provider_status: IntegrationStatus
    request_id: str
    message: str
