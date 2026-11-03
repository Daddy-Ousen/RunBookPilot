# Handoff

## Current state
- Branch: `ui-redesign`. Tag `pre-redesign` = main `d5fb9d5`. Not pushed.
- Phases 0, 1, 2 DONE. Phase 3 (Triage view) BUILT, checkpoint waits on the owner: 2 live checks failed on the LLM upstream (HTTP 504), and 1 design item needs a decision (source runbook text).
- Phase 3 commits: `2123b78` triage view, `dbf73ea` browser-check fixes + screenshots, then a copy-fix + docs commit.
- `app/`, `data/`, `tests/` untouched. `app/safety.py` diff vs `pre-redesign` is empty. pytest 105 passed. innerHTML 0 hits.

## What Phase 3 built
- `static/index.html`: new triage section (input column + result column states) and a new `<template id="result-template">` in plan order: verdict strip, hint, likely cause, steps checklist, commands, `#rmm-check-panel`, source runbooks, `#escalate-banner`, Details (`<details>`, holds `#rmm-telemetry-panel`), `#psa-writeback-panel`.
- `static/js/views/result.js`: fills the template. Command block = `commandBlock()`. Ticks in localStorage `rbp_ticks_<requestId>`. Staged RMM output goes into the RMM check textarea; its button emits `rmm-retriage`. Hint button emits `pick-sample`.
- `static/js/views/triage.js`: samples (5, incl. RDP screenshot sample), queue rows, input errors under the ticket box (`#ticket-error`), request errors in the result column (`#error-region`) with `errorParts()`, 90 s browser timeout, sessionStorage `rbp_last_result` restore on reload, mobile `<details>` handling (forced open at >= 960 px), scroll to the result on one column, `#result-status` sr-only announcement.
- `static/js/copy.js`: `errorParts()`, `verdict()`, `age()`; `queueStatus()` now returns "Pending" too.
- `static/js/api.js`: `timeoutMs` option, `timedOut` flag. `post(path, body, opts)`.
- `static/js/clipboard.js`: `onDone`, `liveText` options.
- CSS: result + command block + states in `views.css`; `.btn-sm` is 40 px below 960 px or on coarse pointers; segmented labels 40 px.

## Open items for the owner
1. Source runbook text: no route returns runbook body. Options: (A) leave as is (ID, rank, note); (B) add a read-only `GET /runbooks/{id}` (backend change, breaks the "no new route" rule); (C) ship a static copy of `data/runbooks/*.md` under `static/` (can drift from `data/`). Recommend A for the deadline.
2. Re-run live when the LLM is healthy: M365 mail sample and one RMM re-triage (UI sent both; upstream gave 504).

## Next step
- Owner reviews Phase 3 checkpoint (`docs/phase3/*.jpg`). Then Phase 4 (Runbooks, Safety lab, Benchmark, Integrations views), Sonnet 5.5 high.

## Gotchas
- Keep these IDs in `index.html` (UI tests check them as text): `nav-tab-triage`, `nav-tab-integrations`, `nav-tab-eval`, `eval-workspace`, `integrations-workspace`, `reasoning-mode-select`, `screenshot-file-input`, `btn-sample-shot-rdp`, `btn-sample-shot-vss`, `rmm-loop-bar`, `btn-draft-runbook`, `btn-hot-index-runbook`, `safety-inspect-form`, `integration-provider-list`, `integration-config-form`, `cfg-fields-grid`, `cfg-webhook-url`, `cfg-test-btn`, `cfg-save-btn`, `pending-queue-panel`, `pending-queue-list`, `rmm-telemetry-panel`, `psa-writeback-panel`, `ticket-input`, `loading-state`, `escalate-banner`, `approval-warning-banner`, `likely-cause-text`, `confidence-badge`, `matched-runbooks-list`, `steps-list`, `commands-list`, `theme-toggle`.
- In `result.js`, resolve template slots BEFORE `container.appendChild(root)`. After that the fragment is empty and `slot()` returns null.
- A reload restores the last result from sessionStorage. To see the empty state, click Clear or open a new tab.
- CSS order: `components.css` loads after `layout.css`. A layout rule that hides a `.btn` or `.badge` needs a stronger selector.
- SVG has no `.hidden` property. Use `toggleAttribute("hidden", ...)`.
- Server: `OPENBLAS_NUM_THREADS=1 .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010`. Port 8000 has a stale old server. Stop 8010 by PID (`netstat -ano | grep :8010`).
- Python Playwright fails. Use the built-in browser. Its screenshots often show the frame BEFORE the last change: take a second screenshot.
- The browser caches `/static/*`. After edits: `await fetch('/static/js/views/result.js', {cache: 'reload'}); location.reload()`.
- Mock `/triage` by patching `window.fetch` in the page; keep the mock source in sessionStorage and `eval` it after each reload.
- Triage is live LLM, 9 to 31 s, and the upstream gave 504 on 3 of 6 calls today.
- `.env` holds the real LLM key. Never print or commit it.

## Active files
- `static/index.html`, `static/css/views.css`, `static/css/components.css`, `static/js/views/{triage,result}.js`, `static/js/{api,copy,clipboard,store}.js`, `progress.md`, `handoff.md`, `docs/phase3/`.
