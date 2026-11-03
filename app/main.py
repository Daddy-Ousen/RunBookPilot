"""FastAPI application entry point for RunbookPilot."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections import deque
from pathlib import Path
from threading import Lock

import httpx
from fastapi import Body, FastAPI, HTTPException, Request
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
    generate_triage,
)
from app.retrieval import DEFAULT_RUNBOOKS_DIR, RunbookIndex
from app.safety import apply_safety_overrides
from app.schema import (
    IntegrationProviderView,
    IntegrationQueueItem,
    IntegrationTestRequest,
    IntegrationTestResult,
    IntegrationUpdateRequest,
    RMMDispatchRequest,
    RMMJobRecord,
    TicketWritebackRequest,
    TicketWritebackResponse,
    TriageRequest,
    TriageResult,
    WebhookAckResponse,
)

DEFAULT_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
MAX_WEBHOOK_PAYLOAD_BYTES = 65_536

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
    async def triage_ticket(payload: TriageRequest, request: Request) -> TriageResult:
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

        top_runbooks = idx.search(payload.ticket, top_k=3)

        try:
            raw_result = await generate_triage(
                payload.ticket,
                top_runbooks,
                request_id=request_id,
                config=llm_config,
                http_client=llm_http_client,
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
        return apply_safety_overrides(raw_result)

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
