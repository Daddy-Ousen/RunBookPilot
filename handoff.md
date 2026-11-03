# Handoff

## Current state
- Branch: `ui-redesign`. Tag `pre-redesign` = main `d5fb9d5`. Not pushed.
- Phase 0 (audit), Phase 1 (design plan, approved) and Phase 2 (foundation) are DONE.
- Phase 2 commits: `4b13760` tokens/base/layout/components CSS, `1c22a27` JS split + shell + router, `b93b8a0` browser-check fixes, `fd5f989` screenshots.
- `app/`, `data/`, `tests/` untouched. `app/safety.py` diff vs `pre-redesign` is empty.

## What Phase 2 built
- `static/index.html`: top bar (Menu button < 768, brand, model badge, index status, theme toggle), left rail (`<nav id="app-nav">`), 5 `<section data-view>` views, toast region, and `<template id="result-template">` (the result skeleton).
- CSS (load order): `tokens.css` (light base; dark under `prefers-color-scheme` unless `data-theme="light"`, and under `data-theme="dark"`), `base.css`, `layout.css` (rail 216 / 64 / menu sheet), `components.css`, `views.css`.
- JS: `main.js` boot; `router.js` (routes, `#eval` alias, unknown hash keeps the view, focus h1, title, `routechange` event); `dom.js` (`el()` textContent only, `badge()`, `notice()`, `icon()`); `api.js` (never throws; `message` from `copy.errorText`, `retryAfter` from header; `triageMeta()`); `copy.js` (term map); `theme.js`; `toast.js`; `store.js` (safe localStorage + shared `state` + `on/emit` bus); `clipboard.js` (`copyButton()`).
- Views: `triage.js` (input, samples, screenshot, mode, queue, submit, error with Retry-After countdown, empty/loading/result states, Run demo), `result.js` (fills the template), `runbooks.js` (index status + list + search), `safety.js`, `benchmark.js`, `integrations.js`.
- Events: `rmm-retriage`, `retriage`, `queue-changed`, `queue-selected`, `index-changed`.

## Next step
- Phase 3: Triage view (Opus 5.5 high). Rebuild the result per `docs/design-plan.md` sections 5 and 6: verdict strip, likely cause, tickable steps (localStorage by request ID), bold command blocks, RMM re-triage box visible below commands, source runbooks as `<details>`, escalation panel, Details (collapsed: request ID, model, mode, time, BM25L scores, safety overrides, RMM telemetry), writeback bar at the end. Edit `result-template` in `index.html` and `static/js/views/result.js`. Input column: samples/queue as `<details>` on mobile.

## Gotchas
- Keep these IDs in `index.html` (UI tests check them as text): `nav-tab-triage`, `nav-tab-integrations`, `nav-tab-eval`, `eval-workspace`, `integrations-workspace`, `reasoning-mode-select`, `screenshot-file-input`, `btn-sample-shot-rdp`, `btn-sample-shot-vss`, `rmm-loop-bar`, `btn-draft-runbook`, `btn-hot-index-runbook`, `safety-inspect-form`, `integration-provider-list`, `integration-config-form`, `cfg-fields-grid`, `cfg-webhook-url`, `cfg-test-btn`, `cfg-save-btn`, `pending-queue-panel`, `pending-queue-list`, `rmm-telemetry-panel`, `psa-writeback-panel`, `ticket-input`, `loading-state`, `escalate-banner`, `approval-warning-banner`, `likely-cause-text`, `confidence-badge`, `matched-runbooks-list`, `steps-list`, `commands-list`, `theme-toggle`.
- In `result.js`, resolve template slots BEFORE `container.appendChild(root)`. After that the fragment is empty and `slot()` returns null.
- CSS order: `components.css` loads after `layout.css`. A layout rule that hides a `.btn` or `.badge` needs a stronger selector (for example `.topbar .menu-btn`).
- SVG has no `.hidden` property. Use `toggleAttribute("hidden", ...)`.
- Run the server with `.venv`: `OPENBLAS_NUM_THREADS=1 .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010`. Port 8000 has a stale old server.
- Python Playwright fails (Node heap out of memory). Use the built-in browser (`preview_start` with `http://127.0.0.1:8010/`). Its screenshots land in the session `tool-results` folder; copy them out.
- The browser caches `/static/*`. After edits run in the page: `await fetch('/static/js/views/result.js', {cache: 'reload'}); location.reload()`.
- Triage is live LLM, 10 to 33 s. To test UI states without LLM calls, patch `window.fetch` in the page (see Phase 2 test approach: mock `/triage` 200 or 429 with `Retry-After`).
- `.env` holds the real LLM key. Never print or commit it.
- Light amber tab fill `#f2b530` is 1.8:1 on white: give the tab a 1 px `--na` border (Phase 3 command block).

## Active files
- `static/index.html`, `static/css/*.css`, `static/js/**/*.js`, `progress.md`, `handoff.md`, `docs/phase2/`.
