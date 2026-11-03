# Handoff

## Current state
- Branch: `ui-redesign` (from main `d5fb9d5`). Tag `pre-redesign` marks the start.
- Phase 0 (audit) is DONE. Files: `docs/ui-audit.md`, 21 screenshots in `docs/audit/`. No app code changed.
- Not pushed. Dev server stopped.

## Next step
- Phase 1: write `docs/design-plan.md` (Opus 5.5 high). Use `docs/ui-audit.md` as input. Stop for the owner's OK.

## Audit top 10 (one line each)
1. 390 px top bar overlaps, page scrolls sideways (584 px).
2. Result order wrong: writeback and badges before diagnosis and commands; no verdict strip.
3. Raw terms in main UI (`read_only`, `needs_approval`, BM25, `executed_on_host`).
4. Queue and RMM data not labelled sample/staged.
5. Empty state is a spec sheet; no demo button.
6. Nav: 3 tabs, "Integrations 0/12" chip, no Runbooks view, sandbox+benchmark mixed.
7. Input column crowded; queue clipped; samples have no description.
8. Errors and loading weak: raw text, no retry, no wait time.
9. Tiny type (11 px mono), 24 font sizes, 17/24 targets under 40 px, some contrast fails.
10. Command block: no tickable steps, no never-executed note near commands, runbook chips do not expand.

## Gotchas
- `.env` holds the real LLM key. Never print or commit it.
- Port 8000 has a stale old server (PID 3952). Run new work on another port (8010 used) with `OPENBLAS_NUM_THREADS=1`.
- Playwright MCP failed to connect. Python Playwright works with system `python` (not `.venv`). Script: scratchpad `shots.py`.
- Triage calls the live LLM (5 to 11 s). Keep calls few.
- Full-page screenshots show sticky-header overlap. This is a capture artifact.

## Active files
- `docs/ui-audit.md`, `docs/audit/*.png`, `progress.md`, `handoff.md`.
