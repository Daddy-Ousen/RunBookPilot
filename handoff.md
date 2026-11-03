# Handoff

## Current state
- Branch: `ui-redesign` (from main `d5fb9d5`). Tag `pre-redesign` marks the start. Not pushed.
- Phase 0 (audit) is DONE: `docs/ui-audit.md`, 21 screenshots in `docs/audit/`.
- Phase 1 (design plan) is APPROVED (2026-11-03) with 2 tweaks, already applied in `docs/design-plan.md`: RMM re-triage stays visible below commands; fonts stay on Google Fonts link.
- No app code changed (`app/`, `static/`, `data/`, `tests/` untouched).

## What Phase 1 decided (short)
- Keep the calm hairline Geist look. Cool slate neutrals. Geist + Geist Mono via the existing Google Fonts link (`display=swap`).
- Brand accent changed from red-orange to cobalt (`#2b4acb` light, `#3d5ae0` fill / `#9aabff` text dark). Reason: red-orange looked like "escalate".
- Risk colors: teal read-only, amber needs approval, red escalate. Confidence and queue priority use neutral ink.
- Bold element: command block with a solid risk tab, 4 px risk rail, ink code surface in both themes, "Not run by RunbookPilot." in every block.
- Layout: rail 216 px at >= 1200, 64 px icons at 768-1199, Menu sheet under the top bar at < 768. Two columns at >= 960.
- Result order: verdict strip, likely cause, tickable steps, commands (read-only, then amber warning + needs-approval), RMM re-triage box (visible), source runbooks (expand), escalation, Details (collapsed), writeback bar ("Staged, not sent to a live PSA.").
- Empty state: "Run demo" button (loads AD lockout sample and analyzes it).

## Next step
- Phase 2: Foundation (Opus 5.5 high). Build exactly the tokens, type scale, components, file split and router in `docs/design-plan.md` sections 2, 3, 4, 7. Keep all old features working.

## Gotchas
- `.env` holds the real LLM key. Never print or commit it.
- Port 8000 has a stale old server (PID 3952). Use port 8010 with `OPENBLAS_NUM_THREADS=1`.
- Playwright MCP fails to connect. Python Playwright works with system `python` (not `.venv`).
- Triage calls the live LLM (5 to 11 s). Keep calls few.
- 429 sends a `Retry-After` header (`app/main.py:262`); use it for the countdown. Same-origin, so the header is readable.
- Light amber tab fill `#f2b530` is 1.8:1 on white. Give it a 1 px `--na` border (plan section 2 says so).
- Keep `#eval` working as an alias for `#benchmark` (old links).
- Contrast script: scratchpad `contrast.py` of the Phase 1 session (not in repo). Re-run the pairs if any token changes.

## Active files
- `docs/design-plan.md`, `progress.md`, `handoff.md`.
