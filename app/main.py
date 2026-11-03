"""FastAPI application entry point for RunbookPilot."""

from __future__ import annotations

import logging
import os
import time
import uuid
from collections import deque
from pathlib import Path
from threading import Lock

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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
from app.schema import TriageRequest, TriageResult

DEFAULT_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

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
) -> FastAPI:
    """Create and configure the RunbookPilot FastAPI application."""
    resolved_runbooks_dir = Path(runbooks_dir) if runbooks_dir is not None else DEFAULT_RUNBOOKS_DIR
    resolved_static_dir = Path(static_dir) if static_dir is not None else DEFAULT_STATIC_DIR

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
