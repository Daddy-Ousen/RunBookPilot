"""Staged RMM and Ticketing/PSA integration catalog and configuration registry.

All connectors operate in staged/standby mode:
- Credentials and endpoint settings can be validated and staged via the API/UI.
- Secret values are masked as '********' in all API responses and never logged.
- Remote command execution on endpoints is permanently disabled across all RMM connectors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from urllib.parse import urlparse

from app.schema import (
    IntegrationCategory,
    IntegrationFieldSpec,
    IntegrationProviderView,
    IntegrationStatus,
    IntegrationSyncMode,
    IntegrationTestRequest,
    IntegrationTestResult,
    IntegrationUpdateRequest,
)

SECRET_MASK = "********"


class IntegrationNotFoundError(KeyError):
    """Raised when a requested provider_id does not exist in the catalog."""


class IntegrationValidationError(ValueError):
    """Raised when submitted configuration fields fail validation."""


@dataclass(frozen=True)
class IntegrationProviderSpec:
    """Static definition of an MSP Ticketing/PSA or RMM integration connector."""

    id: str
    name: str
    category: IntegrationCategory
    protocol: str
    description: str
    capabilities: list[str]
    fields: list[IntegrationFieldSpec]


@dataclass
class _StoredProviderState:
    """Internal mutable configuration state for a single provider."""

    enabled: bool = False
    sync_mode: IntegrationSyncMode = "draft_internal_note"
    values: dict[str, str] = field(default_factory=dict)
    updated_at: str | None = None

    def __repr__(self) -> str:
        return (
            f"_StoredProviderState(enabled={self.enabled!r}, "
            f"sync_mode={self.sync_mode!r}, configured_keys={list(self.values.keys())!r})"
        )


def _is_valid_http_url(value: str) -> bool:
    """Validate that value is an http:// or https:// URL with a network host."""
    if not value or any(ch.isspace() for ch in value):
        return False
    parsed = urlparse(value)
    if parsed.scheme not in ("https", "http"):
        return False
    if not parsed.netloc or "." not in parsed.netloc and "localhost" not in parsed.netloc:
        return False
    return True


PROVIDER_CATALOG: tuple[IntegrationProviderSpec, ...] = (
    # -------------------------------------------------------------------------
    # Ticketing & PSA Systems (6)
    # -------------------------------------------------------------------------
    IntegrationProviderSpec(
        id="connectwise_psa",
        name="ConnectWise PSA",
        category="ticketing",
        protocol="REST API v3.0 + Callback Webhook",
        description=(
            "Ingest service board tickets from ConnectWise Manage and write back grounded "
            "triage diagnoses and display-only PowerShell plans as internal discussion notes."
        ),
        capabilities=[
            "Service board ticket ingest",
            "Internal discussion note draft",
            "Escalation status mapping",
        ],
        fields=[
            IntegrationFieldSpec(
                key="site_url",
                label="ConnectWise site URL",
                field_type="url",
                placeholder="https://psa.msp-alpha.example.test",
                required=True,
                help_text="Base URL of your ConnectWise PSA regional cloud or on-premises server.",
            ),
            IntegrationFieldSpec(
                key="company_id",
                label="Company identifier",
                field_type="text",
                placeholder="msp_alpha",
                required=True,
                help_text="ConnectWise company login identifier used in API authentication.",
            ),
            IntegrationFieldSpec(
                key="client_id",
                label="Developer Client ID",
                field_type="text",
                placeholder="00000000-0000-0000-0000-000000000000",
                required=True,
                help_text="GUID ClientID header issued for the ConnectWise API member integration.",
            ),
            IntegrationFieldSpec(
                key="public_key",
                label="Member public key",
                field_type="text",
                placeholder="cw_pub_key_example_01",
                required=True,
                help_text="API member public key with read access to Service Tickets and Notes.",
            ),
            IntegrationFieldSpec(
                key="private_key",
                label="Member private key",
                field_type="secret",
                placeholder="Enter member private key",
                required=True,
                help_text="API member private key (stored masked, never returned in plaintext).",
            ),
            IntegrationFieldSpec(
                key="service_board",
                label="Default service board",
                field_type="text",
                placeholder="Windows Tier 1 & 2 Helpdesk",
                required=False,
                help_text="Optional service board name filter for inbound webhook events.",
            ),
        ],
    ),
    IntegrationProviderSpec(
        id="autotask_psa",
        name="Datto Autotask PSA",
        category="ticketing",
        protocol="REST API v1.0 + Ticket Callout",
        description=(
            "Receive ticket callout notifications from Datto Autotask queues and post "
            "runbook-grounded internal notes for technician review."
        ),
        capabilities=[
            "Queue ticket callout ingest",
            "Internal ticket note writeback",
            "Queue and priority scoping",
        ],
        fields=[
            IntegrationFieldSpec(
                key="zone_url",
                label="Autotask zone API URL",
                field_type="url",
                placeholder="https://webservices14.autotask.example.test",
                required=True,
                help_text="Zone-specific Autotask REST API endpoint URL for your tenant.",
            ),
            IntegrationFieldSpec(
                key="api_integration_code",
                label="API integration code",
                field_type="text",
                placeholder="AT-RBP-INTEGRATION-01",
                required=True,
                help_text="Tracking identifier assigned to the Autotask API user.",
            ),
            IntegrationFieldSpec(
                key="username",
                label="API username",
                field_type="text",
                placeholder="svc-runbookpilot@msp-alpha.example.test",
                required=True,
                help_text="Dedicated Autotask API user login with ticket read and note write permissions.",
            ),
            IntegrationFieldSpec(
                key="secret",
                label="API secret key",
                field_type="secret",
                placeholder="Enter Autotask API secret",
                required=True,
                help_text="Secret key paired with the Autotask API user account.",
            ),
            IntegrationFieldSpec(
                key="default_queue_id",
                label="Default queue ID",
                field_type="text",
                placeholder="29682833",
                required=False,
                help_text="Optional numeric queue ID filter for inbound tickets.",
            ),
        ],
    ),
    IntegrationProviderSpec(
        id="halopsa",
        name="HaloPSA",
        category="ticketing",
        protocol="OAuth 2.0 Client Credentials + Webhook",
        description=(
            "Connect HaloPSA incident workflows to enrich incoming Windows and M365 tickets "
            "with private triage action notes and matched runbook tags."
        ),
        capabilities=[
            "Incident and request ingest",
            "Private action note writeback",
            "Runbook tag enrichment",
        ],
        fields=[
            IntegrationFieldSpec(
                key="instance_url",
                label="HaloPSA instance URL",
                field_type="url",
                placeholder="https://support.msp-alpha.example.test",
                required=True,
                help_text="Base URL of your HaloPSA hosted or self-hosted instance.",
            ),
            IntegrationFieldSpec(
                key="tenant",
                label="Tenant slug",
                field_type="text",
                placeholder="msp-alpha",
                required=False,
                help_text="Tenant parameter required for HaloPSA cloud-hosted instances.",
            ),
            IntegrationFieldSpec(
                key="client_id",
                label="OAuth Client ID",
                field_type="text",
                placeholder="halo_client_0001",
                required=True,
                help_text="Client ID from HaloPSA Configuration > Integrations > API.",
            ),
            IntegrationFieldSpec(
                key="client_secret",
                label="OAuth Client Secret",
                field_type="secret",
                placeholder="Enter HaloPSA client secret",
                required=True,
                help_text="Client secret for OAuth 2.0 client_credentials token exchange.",
            ),
            IntegrationFieldSpec(
                key="webhook_signing_secret",
                label="Webhook signature secret",
                field_type="secret",
                placeholder="Optional webhook header secret",
                required=False,
                help_text="Optional shared secret used to verify inbound HaloPSA webhook payloads.",
            ),
        ],
    ),
    IntegrationProviderSpec(
        id="servicenow_itsm",
        name="ServiceNow ITSM",
        category="ticketing",
        protocol="Table REST API + Business Rule Webhook",
        description=(
            "Ingest records from the ServiceNow incident table (incident) and append "
            "structured diagnostic steps and risk-labeled commands to work_notes."
        ),
        capabilities=[
            "Incident table ingest",
            "Work notes (work_notes) draft",
            "Assignment group escalation routing",
        ],
        fields=[
            IntegrationFieldSpec(
                key="instance_url",
                label="ServiceNow instance URL",
                field_type="url",
                placeholder="https://mspalpha.service-now.example.test",
                required=True,
                help_text="Full HTTPS base URL of the target ServiceNow instance.",
            ),
            IntegrationFieldSpec(
                key="api_user",
                label="Integration user",
                field_type="text",
                placeholder="svc.runbookpilot",
                required=True,
                help_text="Service account username with itil or custom incident table access.",
            ),
            IntegrationFieldSpec(
                key="api_token",
                label="API password or token",
                field_type="secret",
                placeholder="Enter ServiceNow credential",
                required=True,
                help_text="Service account password or inbound OAuth token secret.",
            ),
            IntegrationFieldSpec(
                key="assignment_group",
                label="Assignment group filter",
                field_type="text",
                placeholder="Windows Server Operations",
                required=False,
                help_text="Optional assignment_group name to scope automatic ticket intake.",
            ),
        ],
    ),
    IntegrationProviderSpec(
        id="jira_service_management",
        name="Jira Service Management",
        category="ticketing",
        protocol="REST API v3 + Automation Webhook",
        description=(
            "Link Jira Service Management IT service desks to draft internal agent comments "
            "containing matched runbooks and PowerShell checks."
        ),
        capabilities=[
            "Service request and incident ingest",
            "Internal agent comment draft",
            "Project key and JQL scoping",
        ],
        fields=[
            IntegrationFieldSpec(
                key="site_url",
                label="Atlassian site URL",
                field_type="url",
                placeholder="https://msp-alpha.atlassian.example.test",
                required=True,
                help_text="Base URL of your Atlassian Cloud site.",
            ),
            IntegrationFieldSpec(
                key="service_account_email",
                label="Service account email",
                field_type="text",
                placeholder="svc-triage@msp-alpha.example.test",
                required=True,
                help_text="Email address of the Atlassian service account.",
            ),
            IntegrationFieldSpec(
                key="api_token",
                label="Atlassian API token",
                field_type="secret",
                placeholder="Enter Atlassian API token",
                required=True,
                help_text="API token generated for the service account.",
            ),
            IntegrationFieldSpec(
                key="project_key",
                label="Service project key",
                field_type="text",
                placeholder="ITOPS",
                required=True,
                help_text="Jira project key (for example ITOPS or WINSD) to monitor.",
            ),
        ],
    ),
    IntegrationProviderSpec(
        id="freshservice",
        name="Freshservice",
        category="ticketing",
        protocol="REST API v2 + Workflow Automator Webhook",
        description=(
            "Receive Freshservice ticket webhooks from Workflow Automator rules and attach "
            "private diagnostic notes for Windows and M365 incidents."
        ),
        capabilities=[
            "Workflow Automator ticket ingest",
            "Private note writeback",
            "Workspace and group filtering",
        ],
        fields=[
            IntegrationFieldSpec(
                key="domain_url",
                label="Freshservice portal URL",
                field_type="url",
                placeholder="https://msp-alpha.freshservice.example.test",
                required=True,
                help_text="HTTPS URL of your Freshservice helpdesk domain.",
            ),
            IntegrationFieldSpec(
                key="api_key",
                label="Freshservice API key",
                field_type="secret",
                placeholder="Enter Freshservice API key",
                required=True,
                help_text="API key associated with a dedicated agent account.",
            ),
            IntegrationFieldSpec(
                key="workspace_id",
                label="Workspace ID",
                field_type="text",
                placeholder="2",
                required=False,
                help_text="Optional workspace numeric identifier for multi-workspace tenants.",
            ),
        ],
    ),
    # -------------------------------------------------------------------------
    # RMM Platforms (6) - Read-only alert/telemetry ingest; NEVER executes scripts
    # -------------------------------------------------------------------------
    IntegrationProviderSpec(
        id="ninjaone_rmm",
        name="NinjaOne RMM",
        category="rmm",
        protocol="OAuth 2.0 + Public API v2 + Webhook",
        description=(
            "Ingest triggered condition alerts and read-only Windows device metadata from "
            "NinjaOne. Remote script or command execution on endpoints is permanently disabled."
        ),
        capabilities=[
            "Condition alert webhook ingest",
            "Read-only device OS and role context",
            "No remote script execution (enforced)",
        ],
        fields=[
            IntegrationFieldSpec(
                key="region_url",
                label="NinjaOne regional URL",
                field_type="url",
                placeholder="https://app.ninjarmm.example.test",
                required=True,
                help_text="Regional NinjaOne API base URL (for example app, eu, oc, or ca).",
            ),
            IntegrationFieldSpec(
                key="client_id",
                label="OAuth Client ID",
                field_type="text",
                placeholder="ninja_client_id_01",
                required=True,
                help_text="Machine-to-machine API application Client ID (monitoring read scope only).",
            ),
            IntegrationFieldSpec(
                key="client_secret",
                label="OAuth Client Secret",
                field_type="secret",
                placeholder="Enter NinjaOne client secret",
                required=True,
                help_text="OAuth Client Secret paired with the NinjaOne API application.",
            ),
            IntegrationFieldSpec(
                key="organization_filter",
                label="Organization scope",
                field_type="text",
                placeholder="All managed organizations",
                required=False,
                help_text="Optional comma-separated list of NinjaOne organization IDs.",
            ),
        ],
    ),
    IntegrationProviderSpec(
        id="datto_rmm",
        name="Datto RMM",
        category="rmm",
        protocol="OAuth 2.0 + REST API v2",
        description=(
            "Pull open monitor alerts and read-only Windows endpoint inventory context from "
            "Datto RMM to enrich PSA tickets. Quick jobs and remote command runs are blocked."
        ),
        capabilities=[
            "Monitor alert ingest",
            "Read-only device audit lookup",
            "No quick-job execution (enforced)",
        ],
        fields=[
            IntegrationFieldSpec(
                key="platform_url",
                label="Datto RMM platform API URL",
                field_type="url",
                placeholder="https://concord-api.centrastage.example.test",
                required=True,
                help_text="Platform API endpoint (Pinotage, Merlot, Concord, Vidal, or Zinfandel).",
            ),
            IntegrationFieldSpec(
                key="api_key",
                label="API key",
                field_type="text",
                placeholder="drmm_pub_key_01",
                required=True,
                help_text="Datto RMM user API Key with read-only alert and device access.",
            ),
            IntegrationFieldSpec(
                key="api_secret_key",
                label="API secret key",
                field_type="secret",
                placeholder="Enter Datto RMM secret key",
                required=True,
                help_text="Datto RMM user API Secret Key.",
            ),
            IntegrationFieldSpec(
                key="site_uid",
                label="Default site UID filter",
                field_type="text",
                placeholder="00000000-1111-2222-3333-444444444444",
                required=False,
                help_text="Optional Datto RMM site UID to restrict alert ingestion.",
            ),
        ],
    ),
    IntegrationProviderSpec(
        id="connectwise_automate",
        name="ConnectWise Automate",
        category="rmm",
        protocol="REST API v1 + Integrator Token",
        description=(
            "Read internal monitor alerts and Windows service/event telemetry from ConnectWise "
            "Automate (LabTech). Remote script scheduling is permanently disabled."
        ),
        capabilities=[
            "Monitor alert ingest",
            "Read-only Windows event and service metadata",
            "No remote script scheduling (enforced)",
        ],
        fields=[
            IntegrationFieldSpec(
                key="server_url",
                label="Automate server URL",
                field_type="url",
                placeholder="https://automate.msp-alpha.example.test",
                required=True,
                help_text="Base HTTPS URL of your ConnectWise Automate server.",
            ),
            IntegrationFieldSpec(
                key="client_id",
                label="Developer Client ID",
                field_type="text",
                placeholder="00000000-0000-0000-0000-000000000001",
                required=True,
                help_text="ConnectWise developer ClientID header value.",
            ),
            IntegrationFieldSpec(
                key="integrator_user",
                label="Integrator username",
                field_type="text",
                placeholder="svc_runbookpilot",
                required=True,
                help_text="Read-only integrator account username.",
            ),
            IntegrationFieldSpec(
                key="integrator_password",
                label="Integrator password",
                field_type="secret",
                placeholder="Enter integrator password",
                required=True,
                help_text="Integrator account password.",
            ),
        ],
    ),
    IntegrationProviderSpec(
        id="nable_ncentral",
        name="N-able N-central",
        category="rmm",
        protocol="JWT Exchange + REST API",
        description=(
            "Ingest active service status alerts and read-only asset metadata from N-able "
            "N-central. Automation policy and remote task execution are disabled."
        ),
        capabilities=[
            "Active service alert ingest",
            "Read-only asset and OS patch context",
            "No automation policy execution (enforced)",
        ],
        fields=[
            IntegrationFieldSpec(
                key="server_url",
                label="N-central server URL",
                field_type="url",
                placeholder="https://ncentral.msp-alpha.example.test",
                required=True,
                help_text="HTTPS base URL of your N-able N-central server.",
            ),
            IntegrationFieldSpec(
                key="jwt_token",
                label="API user JWT",
                field_type="secret",
                placeholder="Enter N-central JSON Web Token",
                required=True,
                help_text="JWT issued for a dedicated read-only API user.",
            ),
            IntegrationFieldSpec(
                key="customer_id",
                label="Customer or SO ID filter",
                field_type="text",
                placeholder="100",
                required=False,
                help_text="Optional Customer or Service Organization numeric ID.",
            ),
        ],
    ),
    IntegrationProviderSpec(
        id="atera_rmm",
        name="Atera RMM",
        category="rmm",
        protocol="REST API v3 + Alert Webhook",
        description=(
            "Ingest threshold alerts and read-only Windows agent diagnostics from Atera RMM "
            "to generate runbook triage plans without executing remote agent scripts."
        ),
        capabilities=[
            "Threshold alert ingest",
            "Read-only Windows agent telemetry",
            "No remote agent command execution (enforced)",
        ],
        fields=[
            IntegrationFieldSpec(
                key="api_url",
                label="Atera API v3 URL",
                field_type="url",
                placeholder="https://app.atera.example.test/api/v3",
                required=True,
                help_text="Atera REST API v3 base URL.",
            ),
            IntegrationFieldSpec(
                key="api_key",
                label="X-API-KEY token",
                field_type="secret",
                placeholder="Enter Atera API key",
                required=True,
                help_text="Atera API key header credential.",
            ),
            IntegrationFieldSpec(
                key="customer_filter",
                label="Customer folder filter",
                field_type="text",
                placeholder="corp-example",
                required=False,
                help_text="Optional customer name or ID filter.",
            ),
        ],
    ),
    IntegrationProviderSpec(
        id="syncro_msp",
        name="SyncroMSP",
        category="rmm",
        protocol="REST API v1 + Automated Alert Webhook",
        description=(
            "Receive RMM alert and ticket webhooks from SyncroMSP and draft private ticket "
            "diagnostics using scoped read/ticket-note permissions only."
        ),
        capabilities=[
            "RMM alert and ticket webhook ingest",
            "Read-only asset summary lookup",
            "Private ticket comment draft",
        ],
        fields=[
            IntegrationFieldSpec(
                key="subdomain_url",
                label="SyncroMSP tenant URL",
                field_type="url",
                placeholder="https://msp-alpha.syncromsp.example.test",
                required=True,
                help_text="Your SyncroMSP tenant HTTPS base URL.",
            ),
            IntegrationFieldSpec(
                key="api_token",
                label="Scoped API token",
                field_type="secret",
                placeholder="Enter SyncroMSP API token",
                required=True,
                help_text="API token with Tickets and Assets read/note scopes (script scopes disabled).",
            ),
        ],
    ),
)

_CATALOG_BY_ID: dict[str, IntegrationProviderSpec] = {spec.id: spec for spec in PROVIDER_CATALOG}


class IntegrationRegistry:
    """Thread-safe registry managing staged RMM and Ticketing integration configs."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._states: dict[str, _StoredProviderState] = {
            spec.id: _StoredProviderState() for spec in PROVIDER_CATALOG
        }

    def _get_spec(self, provider_id: str) -> IntegrationProviderSpec:
        spec = _CATALOG_BY_ID.get(provider_id)
        if spec is None:
            raise IntegrationNotFoundError(f"Unknown integration provider '{provider_id}'.")
        return spec

    @staticmethod
    def _compute_status(enabled: bool, values: dict[str, str]) -> IntegrationStatus:
        has_any_value = any(bool(v.strip()) for v in values.values())
        if enabled:
            return "staged"
        if has_any_value:
            return "paused"
        return "not_configured"

    def _build_view(
        self, spec: IntegrationProviderSpec, state: _StoredProviderState
    ) -> IntegrationProviderView:
        masked_values: dict[str, str] = {}
        has_saved_secrets: dict[str, bool] = {}

        for f_spec in spec.fields:
            raw_val = state.values.get(f_spec.key, "")
            if f_spec.field_type == "secret":
                has_secret = bool(raw_val)
                has_saved_secrets[f_spec.key] = has_secret
                masked_values[f_spec.key] = SECRET_MASK if has_secret else ""
            else:
                masked_values[f_spec.key] = raw_val

        status = self._compute_status(state.enabled, state.values)

        return IntegrationProviderView(
            id=spec.id,
            name=spec.name,
            category=spec.category,
            protocol=spec.protocol,
            description=spec.description,
            capabilities=list(spec.capabilities),
            fields=list(spec.fields),
            webhook_path=f"/integrations/webhooks/{spec.id}",
            remote_execution_allowed=False,
            live_sync_active=False,
            status=status,
            enabled=state.enabled,
            sync_mode=state.sync_mode,
            configured_values=masked_values,
            has_saved_secrets=has_saved_secrets,
            updated_at=state.updated_at,
        )

    def list_providers(self) -> list[IntegrationProviderView]:
        """Return masked views for all 12 catalog providers."""
        with self._lock:
            return [self._build_view(spec, self._states[spec.id]) for spec in PROVIDER_CATALOG]

    def get_provider(self, provider_id: str) -> IntegrationProviderView:
        """Return masked view for a single provider."""
        spec = self._get_spec(provider_id)
        with self._lock:
            return self._build_view(spec, self._states[spec.id])

    def _resolve_effective_values(
        self,
        spec: IntegrationProviderSpec,
        stored_values: dict[str, str],
        submitted_values: dict[str, str],
    ) -> dict[str, str]:
        field_by_key = {f.key: f for f in spec.fields}
        unknown_keys = sorted(set(submitted_values.keys()) - set(field_by_key.keys()))
        if unknown_keys:
            raise IntegrationValidationError(
                f"Unknown configuration field(s) for {spec.name}: {', '.join(unknown_keys)}."
            )

        merged: dict[str, str] = {}
        for f_spec in spec.fields:
            key = f_spec.key
            if key not in submitted_values:
                merged[key] = stored_values.get(key, "")
                continue

            incoming = submitted_values[key].strip()
            if f_spec.field_type == "secret" and incoming == SECRET_MASK:
                # Preserve existing stored secret when masked placeholder is echoed back.
                merged[key] = stored_values.get(key, "")
            else:
                merged[key] = incoming

        return merged

    def update_provider(
        self, provider_id: str, payload: IntegrationUpdateRequest
    ) -> IntegrationProviderView:
        """Validate and save/stage configuration for provider_id."""
        spec = self._get_spec(provider_id)

        with self._lock:
            state = self._states[spec.id]
            effective_values = self._resolve_effective_values(
                spec, state.values, payload.values
            )

            # Validate any non-empty URL fields immediately
            for f_spec in spec.fields:
                val = effective_values.get(f_spec.key, "")
                if f_spec.field_type == "url" and val and not _is_valid_http_url(val):
                    raise IntegrationValidationError(
                        f"Field '{f_spec.label}' must be a valid http:// or https:// URL."
                    )

            # When staging a connector as enabled, all required fields must be present
            if payload.enabled:
                missing_labels = [
                    f_spec.label
                    for f_spec in spec.fields
                    if f_spec.required and not effective_values.get(f_spec.key, "")
                ]
                if missing_labels:
                    raise IntegrationValidationError(
                        f"Cannot stage {spec.name} as ready while required fields are missing: "
                        f"{', '.join(missing_labels)}."
                    )

            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            state.enabled = payload.enabled
            state.sync_mode = payload.sync_mode
            state.values = effective_values
            state.updated_at = now_iso
            return self._build_view(spec, state)

    def reset_provider(self, provider_id: str) -> IntegrationProviderView:
        """Clear stored credentials and reset provider to not_configured."""
        spec = self._get_spec(provider_id)
        with self._lock:
            fresh = _StoredProviderState()
            self._states[spec.id] = fresh
            return self._build_view(spec, fresh)

    def test_provider(
        self, provider_id: str, payload: IntegrationTestRequest | None = None
    ) -> IntegrationTestResult:
        """Perform a staged dry-run validation of required fields and URLs without outbound calls."""
        spec = self._get_spec(provider_id)
        with self._lock:
            state = self._states[spec.id]
            if payload is not None and payload.values is not None:
                effective = self._resolve_effective_values(spec, state.values, payload.values)
            else:
                effective = dict(state.values)

        checked_fields: list[str] = []
        missing_fields: list[str] = []
        invalid_fields: list[str] = []

        for f_spec in spec.fields:
            checked_fields.append(f_spec.key)
            val = effective.get(f_spec.key, "").strip()
            if f_spec.required and not val:
                missing_fields.append(f_spec.key)
                continue
            if val and f_spec.field_type == "url" and not _is_valid_http_url(val):
                invalid_fields.append(f_spec.key)

        if missing_fields or invalid_fields:
            problems: list[str] = []
            if missing_fields:
                problems.append(f"missing required fields ({', '.join(missing_fields)})")
            if invalid_fields:
                problems.append(f"invalid URL format ({', '.join(invalid_fields)})")
            return IntegrationTestResult(
                provider_id=spec.id,
                ok=False,
                status="validation_failed",
                mode="staged_dry_run",
                message=f"Staged validation failed for {spec.name}: {'; '.join(problems)}.",
                checked_fields=checked_fields,
                missing_fields=missing_fields,
                invalid_fields=invalid_fields,
            )

        return IntegrationTestResult(
            provider_id=spec.id,
            ok=True,
            status="staged_ready",
            mode="staged_dry_run",
            message=(
                f"{spec.name} configuration passed schema and endpoint validation. "
                "Connector is staged in standby mode (live network polling is inactive; "
                "remote command execution is permanently disabled)."
            ),
            checked_fields=checked_fields,
            missing_fields=[],
            invalid_fields=[],
        )
