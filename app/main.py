"""FastAPI application entry point for RunbookPilot."""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from collections import deque
from pathlib import Path
from threading import Lock

import httpx
from fastapi import Body, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.integrations import (
    IntegrationNotFoundError,
    IntegrationRegistry,
    IntegrationValidationError,
)
from app.llm import (
    LLMConfig,
    LLMConfigError,
    LLMResponseError,
    LLMTimeoutError,
    LLMUpstreamError,
    generate_runbook_draft,
    generate_triage,
)
from app.retrieval import DEFAULT_RUNBOOKS_DIR, RunbookIndex, parse_runbook_markdown
from app.safety import apply_safety_overrides, classify_command, explain_command_classification
from app.schema import (
    EvalSummaryResponse,
    EvalTicketRow,
    IntegrationProviderView,
    IntegrationQueueItem,
    IntegrationTestRequest,
    IntegrationTestResult,
    IntegrationUpdateRequest,
    RMMDispatchRequest,
    RMMJobRecord,
    RunbookDraftRequest,
    RunbookDraftResult,
    RunbookHotIndexRequest,
    RunbookHotIndexResponse,
    SafetyInspectRequest,
    SafetyInspectResponse,
    TicketWritebackRequest,
    TicketWritebackResponse,
    TriageRequest,
    TriageResult,
    WebhookAckResponse,
)

DEFAULT_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
DEFAULT_EVAL_JSON_PATH = Path(__file__).resolve().parent.parent / "data" / "tickets_eval.json"
MAX_WEBHOOK_PAYLOAD_BYTES = 65_536
_RUNBOOK_CMD_BULLET_RE = re.compile(r"^-\s+`(.+)`\s*$")

# Configure application logging (request IDs only; suppress verbose HTTP client logs).
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger("runbookpilot.api")


class SlidingWindowRateLimiter:
    """In-memory per-client sliding-window rate limiter."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests must be positive.")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive.")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(self, client_key: str) -> tuple[bool, int]:
        """Check and record a hit for client_key. Returns (allowed, retry_after_seconds)."""
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            bucket = self._hits.get(client_key)
            if bucket is None:
                bucket = deque()
                self._hits[client_key] = bucket

            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self.max_requests:
                retry_after = max(1, int(self.window_seconds - (now - bucket[0])) + 1)
                return False, retry_after

            bucket.append(now)

            # Periodic cleanup of idle client keys when map grows
            if len(self._hits) > 1024:
                stale_keys = [k for k, q in self._hits.items() if not q or q[-1] <= cutoff]
                for k in stale_keys:
                    del self._hits[k]

            return True, 0


def _extract_client_ip(request: Request) -> str:
    """Resolve client IP safely across Vercel edge proxy and direct local connections."""
    if os.environ.get("VERCEL"):
        vercel_ip = request.headers.get("x-vercel-forwarded-for", "").split(",")[0].strip()
        if vercel_ip:
            return vercel_ip
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else "unknown"


def _read_positive_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        val = int(raw)
    except ValueError:
        return default
    return val if val > 0 else default


def create_app(
    *,
    runbooks_dir: Path | str | None = None,
    static_dir: Path | str | None = None,
    rate_limit_requests: int | None = None,
    rate_limit_window_seconds: float | None = None,
    llm_config: LLMConfig | None = None,
    llm_http_client: httpx.AsyncClient | None = None,
    integrations_registry: IntegrationRegistry | None = None,
) -> FastAPI:
    """Create and configure the RunbookPilot FastAPI application."""
    resolved_runbooks_dir = Path(runbooks_dir) if runbooks_dir is not None else DEFAULT_RUNBOOKS_DIR
    resolved_static_dir = Path(static_dir) if static_dir is not None else DEFAULT_STATIC_DIR
    registry = integrations_registry if integrations_registry is not None else IntegrationRegistry()

    max_reqs = (
        rate_limit_requests
        if rate_limit_requests is not None
        else _read_positive_int_env("RATE_LIMIT_REQUESTS", 15)
    )
    window_secs = (
        rate_limit_window_seconds
        if rate_limit_window_seconds is not None
        else float(_read_positive_int_env("RATE_LIMIT_WINDOW_SECONDS", 60))
    )

    limiter = SlidingWindowRateLimiter(max_requests=max_reqs, window_seconds=window_secs)
    index_cache: dict[str, RunbookIndex] = {}
    index_lock = Lock()

    def get_index() -> RunbookIndex:
        cached = index_cache.get("index")
        if cached is not None:
            return cached
        with index_lock:
            cached = index_cache.get("index")
            if cached is None:
                cached = RunbookIndex.from_directory(resolved_runbooks_dir)
                index_cache["index"] = cached
            return cached

    application = FastAPI(
        title="RunbookPilot",
        description="Grounded Windows IT runbook triage assistant (display-only commands).",
        version="1.0.0",
    )

    @application.middleware("http")
    async def request_id_logging_middleware(request: Request, call_next):
        request_id = uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            logger.exception(
                "request_id=%s method=%s path=%s status=500 duration_ms=%.1f",
                request_id,
                request.method,
                request.url.path,
                elapsed_ms,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error.",
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_id=%s method=%s path=%s status=%d duration_ms=%.1f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    @application.get("/health")
    async def health() -> dict[str, object]:
        try:
            idx = get_index()
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Runbook index unavailable: {exc}",
            ) from exc
        return {
            "status": "ok",
            "runbooks_loaded": len(idx.runbooks),
        }

    @application.get("/runbooks")
    async def list_runbooks() -> list[dict[str, str]]:
        try:
            idx = get_index()
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Runbook index unavailable: {exc}",
            ) from exc
        return [{"id": rb.id, "title": rb.title} for rb in idx.runbooks]

    @application.post("/triage", response_model=TriageResult)
    async def triage_ticket(
        payload: TriageRequest, request: Request, response: Response
    ) -> TriageResult:
        request_id: str = getattr(request.state, "request_id", "unknown")
        client_ip = _extract_client_ip(request)

        allowed, retry_after = limiter.allow(client_ip)
        if not allowed:
            logger.warning("request_id=%s rate_limited=true retry_after_s=%d", request_id, retry_after)
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        try:
            idx = get_index()
        except (FileNotFoundError, ValueError) as exc:
            logger.error("request_id=%s runbook_load_error=%s", request_id, exc.__class__.__name__)
            raise HTTPException(
                status_code=503,
                detail=f"Runbook index unavailable: {exc}",
            ) from exc

        search_query = (
            f"{payload.ticket}\n{payload.screenshot_caption}"
            if payload.screenshot_caption
            else payload.ticket
        )
        top_runbooks = idx.search(search_query, top_k=3)

        try:
            raw_result = await generate_triage(
                payload.ticket,
                top_runbooks,
                request_id=request_id,
                config=llm_config,
                http_client=llm_http_client,
                screenshot_data_url=payload.screenshot_data_url,
                screenshot_caption=payload.screenshot_caption,
                rmm_diagnostic_output=payload.rmm_diagnostic_output,
                reasoning_mode=payload.reasoning_mode,
            )
        except LLMConfigError as exc:
            logger.error("request_id=%s llm_config_error=true", request_id)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except LLMTimeoutError as exc:
            logger.error("request_id=%s llm_timeout=true", request_id)
            raise HTTPException(status_code=504, detail=str(exc)) from exc
        except (LLMUpstreamError, LLMResponseError) as exc:
            logger.error("request_id=%s llm_upstream_or_parse_error=%s", request_id, exc.__class__.__name__)
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        # Deterministically override every command's risk label (never trust LLM risk labels).
        final_result = apply_safety_overrides(raw_result)
        overrides_count = sum(
            1
            for raw_cmd, fin_cmd in zip(raw_result.commands, final_result.commands)
            if raw_cmd.risk != fin_cmd.risk
        )
        active_model_name = (
            llm_config.model
            if llm_config is not None
            else (os.environ.get("LLM_MODEL", "muse-spark-1.3").strip() or "muse-spark-1.3")
        )
        response.headers["X-Meta-Model"] = active_model_name
        response.headers["X-Reasoning-Mode"] = payload.reasoning_mode
        response.headers["X-BM25-Scores"] = json.dumps(
            {item.runbook.id: round(item.score, 2) for item in top_runbooks}
        )
        response.headers["X-Safety-Overrides"] = str(overrides_count)
        return final_result

    @application.post("/safety/inspect", response_model=SafetyInspectResponse)
    async def inspect_command_safety(payload: SafetyInspectRequest) -> SafetyInspectResponse:
        risk, reason, stages = explain_command_classification(payload.command)
        return SafetyInspectResponse(
            command=payload.command,
            risk=risk,
            reason=reason,
            stages=stages,
            executed_on_host=False,
        )

    @application.get("/eval/summary", response_model=EvalSummaryResponse)
    async def get_eval_summary() -> EvalSummaryResponse:
        try:
            idx = get_index()
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Runbook index unavailable: {exc}",
            ) from exc

        candidate_eval_path = resolved_runbooks_dir.parent / "tickets_eval.json"
        eval_path = candidate_eval_path if candidate_eval_path.is_file() else DEFAULT_EVAL_JSON_PATH
        if not eval_path.is_file():
            raise HTTPException(status_code=404, detail="Evaluation benchmark dataset not found.")

        raw_items = json.loads(eval_path.read_text(encoding="utf-8"))
        total_tickets = len(raw_items)
        covered_tickets = 0
        escalation_tickets = 0
        bm25_top3_hits = 0
        rows: list[EvalTicketRow] = []

        for item in raw_items:
            ticket_id = str(item["id"])
            ticket_text = str(item["ticket"])
            expected_rb: str | None = item.get("expected_runbook_id")
            expected_escalate = bool(item.get("expected_escalate", expected_rb is None))

            top_3 = idx.search(ticket_text, top_k=3)
            top_matches = [
                {
                    "id": scored.runbook.id,
                    "title": scored.runbook.title,
                    "score": round(scored.score, 2),
                }
                for scored in top_3
            ]
            retrieved_ids = [scored.runbook.id for scored in top_3]

            if expected_rb is not None:
                covered_tickets += 1
                hit = expected_rb in retrieved_ids
                if hit:
                    bm25_top3_hits += 1
            else:
                escalation_tickets += 1
                hit = True

            rows.append(
                EvalTicketRow(
                    ticket_id=ticket_id,
                    expected_runbook_id=expected_rb,
                    expected_escalate=expected_escalate,
                    top_matches=top_matches,
                    retrieval_hit=hit,
                )
            )

        commands_audited = 0
        mislabeled_needs_approval = 0
        for rb in idx.runbooks:
            section: str | None = None
            for line in rb.body.splitlines():
                stripped = line.strip()
                if stripped.startswith("## Checks"):
                    section = "checks"
                    continue
                if stripped.startswith("## Fixes"):
                    section = "fixes"
                    continue
                if stripped.startswith("## "):
                    section = None
                    continue
                if section in ("checks", "fixes"):
                    match = _RUNBOOK_CMD_BULLET_RE.match(stripped)
                    if match:
                        cmd_str = match.group(1).strip()
                        commands_audited += 1
                        classified = classify_command(cmd_str)
                        if section == "fixes" and classified != "needs_approval":
                            mislabeled_needs_approval += 1

        hit_rate = round((bm25_top3_hits / covered_tickets) * 100.0, 1) if covered_tickets else 0.0
        return EvalSummaryResponse(
            total_tickets=total_tickets,
            covered_tickets=covered_tickets,
            escalation_tickets=escalation_tickets,
            bm25_top3_hits=bm25_top3_hits,
            bm25_top3_hit_rate=hit_rate,
            runbooks_audited=len(idx.runbooks),
            commands_audited=commands_audited,
            mislabeled_needs_approval=mislabeled_needs_approval,
            rows=rows,
        )

    @application.post("/runbooks/draft", response_model=RunbookDraftResult)
    async def draft_new_runbook(
        payload: RunbookDraftRequest, request: Request
    ) -> RunbookDraftResult:
        request_id: str = getattr(request.state, "request_id", "unknown")
        client_ip = _extract_client_ip(request)

        allowed, retry_after = limiter.allow(client_ip)
        if not allowed:
            logger.warning(
                "request_id=%s draft_rate_limited=true retry_after_s=%d", request_id, retry_after
            )
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        try:
            draft = await generate_runbook_draft(
                payload.ticket,
                escalate_reason=payload.escalate_reason,
                request_id=request_id,
                config=llm_config,
                http_client=llm_http_client,
            )
        except LLMConfigError as exc:
            logger.error("request_id=%s draft_llm_config_error=true", request_id)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except LLMTimeoutError as exc:
            logger.error("request_id=%s draft_llm_timeout=true", request_id)
            raise HTTPException(status_code=504, detail=str(exc)) from exc
        except (LLMUpstreamError, LLMResponseError) as exc:
            logger.error(
                "request_id=%s draft_llm_error=%s", request_id, exc.__class__.__name__
            )
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        logger.info("request_id=%s runbook_draft_generated=%s", request_id, draft.id)
        return draft

    @application.post("/runbooks/index", response_model=RunbookHotIndexResponse)
    async def hot_index_runbook(
        payload: RunbookHotIndexRequest, request: Request
    ) -> RunbookHotIndexResponse:
        request_id: str = getattr(request.state, "request_id", "unknown")
        try:
            idx = get_index()
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Runbook index unavailable: {exc}",
            ) from exc

        try:
            parsed_rb = parse_runbook_markdown(payload.markdown)
            with index_lock:
                idx.add_or_replace_runbook(parsed_rb)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        logger.info(
            "request_id=%s runbook_hot_indexed=%s total=%d",
            request_id,
            parsed_rb.id,
            len(idx.runbooks),
        )
        return RunbookHotIndexResponse(
            id=parsed_rb.id,
            title=parsed_rb.title,
            tags=list(parsed_rb.tags),
            total_runbooks_indexed=len(idx.runbooks),
            message=(
                f"Runbook '{parsed_rb.id}' hot-indexed into active BM25 session corpus "
                f"({len(idx.runbooks)} runbooks active)."
            ),
        )

    @application.get("/integrations", response_model=list[IntegrationProviderView])
    async def list_integrations() -> list[IntegrationProviderView]:
        return registry.list_providers()

    @application.get("/integrations/queue", response_model=list[IntegrationQueueItem])
    async def list_integration_queue(
        provider_id: str | None = None, staged_only: bool = False
    ) -> list[IntegrationQueueItem]:
        return registry.list_queue(provider_id=provider_id, staged_only=staged_only)

    @application.get("/integrations/rmm/jobs", response_model=list[RMMJobRecord])
    async def list_staged_rmm_jobs() -> list[RMMJobRecord]:
        return registry.list_rmm_jobs()

    @application.post("/integrations/rmm/dispatch", response_model=RMMJobRecord)
    async def dispatch_staged_rmm_job(
        payload: RMMDispatchRequest, request: Request
    ) -> RMMJobRecord:
        request_id: str = getattr(request.state, "request_id", "unknown")
        try:
            job = registry.dispatch_rmm_command(payload)
        except IntegrationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except IntegrationValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        logger.info(
            "request_id=%s rmm_job_queued=%s provider=%s risk=%s",
            request_id,
            job.job_id,
            job.rmm_provider_id,
            job.classified_risk,
        )
        return job

    @application.post(
        "/integrations/tickets/{ticket_id}/writeback",
        response_model=TicketWritebackResponse,
    )
    async def writeback_psa_ticket(
        ticket_id: str, payload: TicketWritebackRequest, request: Request
    ) -> TicketWritebackResponse:
        request_id: str = getattr(request.state, "request_id", "unknown")
        try:
            result = registry.writeback_ticket(ticket_id, payload)
        except IntegrationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except IntegrationValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        logger.info(
            "request_id=%s ticket_writeback=%s provider=%s action=%s",
            request_id,
            ticket_id,
            payload.provider_id,
            payload.action,
        )
        return result

    @application.get("/integrations/{provider_id}", response_model=IntegrationProviderView)
    async def get_integration(provider_id: str) -> IntegrationProviderView:
        try:
            return registry.get_provider(provider_id)
        except IntegrationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @application.put("/integrations/{provider_id}", response_model=IntegrationProviderView)
    async def update_integration(
        provider_id: str, payload: IntegrationUpdateRequest, request: Request
    ) -> IntegrationProviderView:
        request_id: str = getattr(request.state, "request_id", "unknown")
        try:
            updated = registry.update_provider(provider_id, payload)
        except IntegrationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except IntegrationValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        logger.info(
            "request_id=%s integration_updated=%s status=%s",
            request_id,
            provider_id,
            updated.status,
        )
        return updated

    @application.delete("/integrations/{provider_id}", response_model=IntegrationProviderView)
    async def reset_integration(provider_id: str, request: Request) -> IntegrationProviderView:
        request_id: str = getattr(request.state, "request_id", "unknown")
        try:
            reset_view = registry.reset_provider(provider_id)
        except IntegrationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        logger.info("request_id=%s integration_reset=%s", request_id, provider_id)
        return reset_view

    @application.post("/integrations/{provider_id}/test", response_model=IntegrationTestResult)
    async def test_integration(
        provider_id: str,
        request: Request,
        payload: IntegrationTestRequest | None = Body(default=None),
    ) -> IntegrationTestResult:
        request_id: str = getattr(request.state, "request_id", "unknown")
        try:
            result = registry.test_provider(provider_id, payload)
        except IntegrationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except IntegrationValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        logger.info(
            "request_id=%s integration_tested=%s status=%s",
            request_id,
            provider_id,
            result.status,
        )
        return result

    @application.post(
        "/integrations/webhooks/{provider_id}",
        response_model=WebhookAckResponse,
        status_code=202,
    )
    async def receive_integration_webhook(
        provider_id: str, request: Request
    ) -> WebhookAckResponse:
        request_id: str = getattr(request.state, "request_id", "unknown")
        client_ip = _extract_client_ip(request)

        allowed, retry_after = limiter.allow(client_ip)
        if not allowed:
            logger.warning(
                "request_id=%s webhook_rate_limited=true retry_after_s=%d",
                request_id,
                retry_after,
            )
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        try:
            provider_view = registry.get_provider(provider_id)
        except IntegrationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        raw_body = await request.body()
        if len(raw_body) > MAX_WEBHOOK_PAYLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Webhook payload exceeds maximum size of {MAX_WEBHOOK_PAYLOAD_BYTES} bytes.",
            )

        queued_ticket_id: str | None = None
        if raw_body.strip():
            try:
                parsed = json.loads(raw_body)
            except ValueError as exc:
                raise HTTPException(
                    status_code=422, detail="Webhook payload must be valid JSON."
                ) from exc
            if not isinstance(parsed, (dict, list)):
                raise HTTPException(
                    status_code=422, detail="Webhook JSON root must be an object or array."
                )
            if isinstance(parsed, dict):
                queued_item = registry.enqueue_webhook_event(provider_id, parsed)
                if queued_item is not None:
                    queued_ticket_id = queued_item.id

        # Log request_id and provider_id only; never log webhook payload content.
        logger.info(
            "request_id=%s webhook_standby_ack=%s provider_status=%s",
            request_id,
            provider_id,
            provider_view.status,
        )
        return WebhookAckResponse(
            provider_id=provider_view.id,
            accepted=True,
            mode="staged_standby",
            provider_status=provider_view.status,
            request_id=request_id,
            queued_ticket_id=queued_ticket_id,
            message=(
                f"{provider_view.name} webhook endpoint is ready in standby mode. "
                "Live automated triage dispatch is currently inactive."
            ),
        )

    @application.get("/", include_in_schema=False)
    async def serve_ui() -> FileResponse:
        index_html = resolved_static_dir / "index.html"
        if not index_html.is_file():
            raise HTTPException(status_code=404, detail="UI static/index.html not found.")
        return FileResponse(index_html)

    if resolved_static_dir.is_dir():
        application.mount("/static", StaticFiles(directory=str(resolved_static_dir)), name="static")

    return application


app = create_app()
