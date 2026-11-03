# Handoff

## Current state
- Branch: `ui-redesign` (from main `d5fb9d5`). Tag `pre-redesign` marks the start.
- Plan: `UI_REDESIGN_PLAN.md`. State: `progress.md`.
- Phase 0 (audit) is next. No UI code changed yet.

## Next step
- Phase 0: run the app, screenshot every view at 1440, 768, 390 px, write `docs/ui-audit.md` (10 worst problems). Stop and show the owner.

## Gotchas
- `.env` holds the real LLM key. Never print it, never commit it.
- Triage calls a live LLM. Rate limits (429) can happen. Do not spam it.
- Screenshots go to `docs/audit/` so the owner can see them.
- Only one session at a time uses the shared Playwright browser.

## Active files
- `static/index.html`, `app/main.py` (read only for routes), `progress.md`, `handoff.md`.
