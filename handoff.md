# Handoff

## Current state
- Branch: `ui-redesign`. Tag `pre-redesign` = main `d5fb9d5`. Not pushed. Server stopped, browser tab closed.
- Phases 0 to 4 DONE and checked. Next: Phase 5 (Polish), then Phase 6 (Verify, Vercel preview, merge). UI work stops Nov 4, 12:00 Dhaka.
- Phase 4 commits: `66c3bc8` static runbook copy, `c7d84b6` renderer + source runbooks + Runbooks logic, `256b66d` views rebuild, then the Integrations + fixes commit and a docs commit.
- `app/`, `data/`, `tests/` untouched. `app/safety.py` diff vs `pre-redesign` empty. pytest 105 passed. innerHTML 0 hits.

## What Phase 4 built
- `static/runbooks/*.md` (byte copy of `data/runbooks/`) + `static/runbooks/index.json` (runbook ID to file; equals live `/runbooks`).
- `static/js/markdown.js` (safe renderer), `static/js/runbook-text.js` (fetch + cache, session text first).
- `static/js/views/runbooks.js`: list + search + reader, "Added in this session" badge, `onRunbooksShown`, `state.openRunbook`. Text of all 18 loads only after the view opens.
- `static/js/views/result.js`: Source runbooks `<details>` fetch text on first open, "Open in Runbooks" link.
- `static/js/views/{safety,benchmark,integrations}.js` and the matching sections of `static/index.html`; styles in `static/css/views.css` (Runbooks, Safety lab, Benchmark, Integrations blocks, `.md-*` styles).
- `static/js/copy.js`: `plainRisk()`.
- Live checks: M365 mail 200 (14.0 s), RMM re-triage 200 (16.6 s). 2 of 4 calls used.
- Screenshots: `docs/phase4/`.

## Next step (Phase 5, Sonnet 5.5 high)
- Responsive pass at 1024 (not walked yet), a11y pass (screen reader names, `aria-live`, contrast spot check in the browser), copy pass, meta tags (`og:title`, `og:description`), favicon check, remove one decoration.
- Known small gaps to look at: Triage inline links in the hint line are 20 px high; `.btn-sm` is 32 px on desktop (queue buttons, sample screenshot buttons); `prefers-reduced-motion` not checked in the browser; clipboard Copy only checked with the fallback.
- Phase 6 must run: pytest, innerHTML grep, `git diff pre-redesign -- app/safety.py`, `diff -r data/runbooks static/runbooks` (only `index.json` differs), Lighthouse a11y >= 95, 390 px, keyboard run, Vercel preview, owner review, merge.

## Gotchas
- Keep these IDs in `index.html` (UI tests check them as text): `nav-tab-triage`, `nav-tab-integrations`, `nav-tab-eval`, `eval-workspace`, `integrations-workspace`, `reasoning-mode-select`, `screenshot-file-input`, `btn-sample-shot-rdp`, `btn-sample-shot-vss`, `rmm-loop-bar`, `btn-draft-runbook`, `btn-hot-index-runbook`, `safety-inspect-form`, `integration-provider-list`, `integration-config-form`, `cfg-fields-grid`, `cfg-webhook-url`, `cfg-test-btn`, `cfg-save-btn`, `pending-queue-panel`, `pending-queue-list`, `rmm-telemetry-panel`, `psa-writeback-panel`, `ticket-input`, `loading-state`, `escalate-banner`, `approval-warning-banner`, `likely-cause-text`, `confidence-badge`, `matched-runbooks-list`, `steps-list`, `commands-list`, `theme-toggle`.
- In `result.js`, resolve template slots BEFORE `container.appendChild(root)`.
- CSS order: `components.css` loads after `layout.css`. A layout rule that hides a `.btn` or `.badge` needs a stronger selector.
- SVG has no `.hidden` property. Use `toggleAttribute("hidden", ...)`.
- Server: `OPENBLAS_NUM_THREADS=1 .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010`. Port 8000 has a stale old server. Stop 8010 by PID (`netstat -ano | grep :8010`).
- Python Playwright fails. Use the built-in browser (`resize_window` for 1440/768/390 and light/dark). Its screenshots often show the frame BEFORE the last change: take a second screenshot. Saved shots are in the tool-results folder; copy them into `docs/`.
- The browser caches `/static/*`. After edits: `await fetch('/static/js/views/x.js', {cache: 'reload'}); location.reload()`.
- Mock `/triage` by patching `window.fetch` in the page. The live M365 result is a good mock body.
- Triage is live LLM, 8 to 33 s. Upstream 504 hit 3 of 6 calls in Phase 3, 0 of 2 in Phase 4.
- Git autocrlf warns on `static/runbooks/*.md`. Harmless.
- `.env` holds the real LLM key. Never print or commit it.

## Active files
- `static/index.html`, `static/css/views.css`, `static/js/{markdown,runbook-text,copy,store,main}.js`, `static/js/views/{runbooks,safety,benchmark,integrations,result}.js`, `static/runbooks/`, `progress.md`, `handoff.md`, `docs/phase4/`.
