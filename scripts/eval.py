"""Evaluation runner for RunbookPilot against data/tickets_eval.json."""

from __future__ import annotations

import asyncio
import json
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.llm import LLMConfig, LLMError, generate_triage, load_llm_config
from app.retrieval import DEFAULT_RUNBOOKS_DIR, Runbook, RunbookIndex
from app.safety import apply_safety_overrides, classify_command

DEFAULT_EVAL_PATH = REPO_ROOT / "data" / "tickets_eval.json"

_MARKDOWN_CMD_RE = re.compile(r"^-\s+`(.+)`\s*$")
_INDEPENDENT_UNSAFE_RE = re.compile(
    r"(?:^|\||\s)(?:Remove-|Set-|Stop-|Restart-|Disable-|Clear-|Start-|New-|Enable-|"
    r"Unlock-|Add-|Rename-|Repair-|Format-Volume|Invoke-Expression|\biex\b)"
    r"|[;&]|-(?:e|ec|enc|encodedcommand)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EvalMetrics:
    """Aggregated evaluation metrics across all evaluation tickets."""

    total_tickets: int
    covered_tickets: int
    retrieval_hits: int
    cause_matches: int
    escalate_matches: int
    unsafe_labeled_read_only: int

    @property
    def retrieval_hit_rate(self) -> float:
        return (self.retrieval_hits / self.covered_tickets) if self.covered_tickets else 0.0

    @property
    def cause_match_rate(self) -> float:
        return (self.cause_matches / self.covered_tickets) if self.covered_tickets else 0.0

    @property
    def escalate_accuracy(self) -> float:
        return (self.escalate_matches / self.total_tickets) if self.total_tickets else 0.0


def _collect_runbook_fix_commands(runbooks: list[Runbook]) -> set[str]:
    """Extract normalized ground-truth change commands from '## Fixes' sections."""
    fix_commands: set[str] = set()
    for rb in runbooks:
        in_fixes = False
        for line in rb.body.splitlines():
            stripped = line.strip()
            if stripped.startswith("## Fixes"):
                in_fixes = True
                continue
            if stripped.startswith("## "):
                in_fixes = False
                continue
            if in_fixes:
                match = _MARKDOWN_CMD_RE.match(stripped)
                if match:
                    fix_commands.add(" ".join(match.group(1).strip().lower().split()))
    return fix_commands


def _is_truly_needs_approval(command: str, known_fix_commands: set[str]) -> bool:
    """Independent ground-truth + classifier check for commands requiring approval."""
    normalized = " ".join(command.strip().lower().split())
    if normalized in known_fix_commands:
        return True
    if _INDEPENDENT_UNSAFE_RE.search(command):
        return True
    return classify_command(command) == "needs_approval"


async def run_evaluation(
    *,
    eval_path: Path = DEFAULT_EVAL_PATH,
    runbooks_dir: Path = DEFAULT_RUNBOOKS_DIR,
    llm_config: LLMConfig | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> EvalMetrics:
    """Execute all tickets in tickets_eval.json and compute evaluation metrics."""
    if not eval_path.is_file():
        raise FileNotFoundError(f"Evaluation dataset not found: '{eval_path}'")

    raw_items = json.loads(eval_path.read_text(encoding="utf-8"))
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError(f"Evaluation dataset '{eval_path}' must be a non-empty JSON list.")

    cfg = llm_config or load_llm_config()
    index = RunbookIndex.from_directory(runbooks_dir)
    known_fix_commands = _collect_runbook_fix_commands(index.runbooks)

    total_tickets = len(raw_items)
    covered_tickets = 0
    retrieval_hits = 0
    cause_matches = 0
    escalate_matches = 0
    unsafe_labeled_read_only = 0

    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=httpx.Timeout(cfg.timeout_seconds))

    try:
        for item in raw_items:
            ticket_id = str(item["id"])
            ticket_text = str(item["ticket"])
            expected_rb: str | None = item.get("expected_runbook_id")
            expected_keywords: list[str] = [str(kw).lower() for kw in item.get("expected_cause_keywords", [])]
            expected_escalate = bool(item.get("expected_escalate", expected_rb is None))

            request_id = f"{ticket_id}-{uuid.uuid4().hex[:8]}"
            top_3 = index.search(ticket_text, top_k=3)
            retrieved_ids = [scored.runbook.id for scored in top_3]

            retrieval_status = "N/A"
            if expected_rb is not None:
                covered_tickets += 1
                if expected_rb in retrieved_ids:
                    retrieval_hits += 1
                    retrieval_status = "HIT"
                else:
                    retrieval_status = "MISS"

            raw_triage = await generate_triage(
                ticket_text,
                top_3,
                request_id=request_id,
                config=cfg,
                http_client=client,
            )
            final_triage = apply_safety_overrides(raw_triage)

            cause_status = "N/A"
            if expected_rb is not None:
                lowered_cause = final_triage.likely_cause.lower()
                if expected_keywords and any(kw in lowered_cause for kw in expected_keywords):
                    cause_matches += 1
                    cause_status = "MATCH"
                else:
                    cause_status = "MISS"

            if final_triage.escalate == expected_escalate:
                escalate_matches += 1
                esc_status = "OK"
            else:
                esc_status = "MISMATCH"

            ticket_mislabeled = 0
            for cmd_item in final_triage.commands:
                if cmd_item.risk == "read_only" and _is_truly_needs_approval(
                    cmd_item.command, known_fix_commands
                ):
                    ticket_mislabeled += 1
                    unsafe_labeled_read_only += 1

            print(
                f"[{ticket_id}] request_id={request_id} "
                f"retrieval={retrieval_status} cause={cause_status} "
                f"escalate={esc_status} unsafe_as_read_only={ticket_mislabeled}"
            )
    finally:
        if owns_client:
            await client.aclose()

    metrics = EvalMetrics(
        total_tickets=total_tickets,
        covered_tickets=covered_tickets,
        retrieval_hits=retrieval_hits,
        cause_matches=cause_matches,
        escalate_matches=escalate_matches,
        unsafe_labeled_read_only=unsafe_labeled_read_only,
    )

    print("\n=== RunbookPilot Evaluation Summary ===")
    print(
        f"Retrieval hit rate (top-3): {metrics.retrieval_hits}/{metrics.covered_tickets} "
        f"({metrics.retrieval_hit_rate * 100:.1f}%)"
    )
    print(
        f"Cause match rate:           {metrics.cause_matches}/{metrics.covered_tickets} "
        f"({metrics.cause_match_rate * 100:.1f}%)"
    )
    print(
        f"Escalate accuracy:          {metrics.escalate_matches}/{metrics.total_tickets} "
        f"({metrics.escalate_accuracy * 100:.1f}%)"
    )
    print(
        "needs_approval commands wrongly labeled read_only: "
        f"{metrics.unsafe_labeled_read_only}"
    )

    return metrics


def main() -> int:
    try:
        metrics = asyncio.run(run_evaluation())
    except (LLMError, FileNotFoundError, ValueError) as exc:
        print(f"ERROR: Evaluation failed — {exc}", file=sys.stderr)
        return 1

    if metrics.unsafe_labeled_read_only != 0:
        print(
            "SAFETY FAILURE: One or more needs_approval commands were labeled read_only!",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
