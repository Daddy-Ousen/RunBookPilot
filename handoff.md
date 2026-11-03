# Handoff

## Current state
- Branch: `ui-redesign`. Tag `pre-redesign` = main `d5fb9d5`. Not pushed. Server stopped, browser tab closed.
- Phases 0 to 5 DONE and checked. Next: Phase 6 (Verify, Vercel preview, phone test, owner review, merge). UI work stops Nov 4, 12:00 Dhaka.
- Phase 5 commits: `61f1936` (40 px targets, hint line), `c4be2ef` (head meta, favicon, focus to result/error, sample buttons, skeleton shimmer removed), `d04ec9e` (README + screenshots), then a docs commit (`progress.md`, `handoff.md`).
- `app/`, `data/`, `tests/` untouched. `app/safety.py` diff vs `pre-redesign` empty. pytest 105 passed. innerHTML 0 hits. `diff -r data/runbooks static/runbooks` shows only `index.json`.

## What Phase 5 did
- Lighthouse accessibility 100 on `/#triage` (empty state), with Edge. axe-core: 0 violations on 5 routes, light and dark, result on screen.
- All targets >= 40 px at 1440, 1024, 768, 390. No sideways scroll. One `<h1>` per view. No layout shift on result arrival.
- `prefers-reduced-motion` and real-clipboard Copy checked in headless Edge. Keyboard-only full triage flow works.
- Focus goes to the verdict strip (result) or error panel (failure). Desktop Samples/Queue headers are out of the tab order.
- Head: title, description, og tags, theme-color (light/dark, follows the toggle), `static/favicon.svg` (cobalt).
- Copy: sample screenshot buttons now "Attach RDP sample" / "Attach VSS sample". README has a "User interface" section.
- Removed decoration: skeleton shimmer (gradient + endless animation).
- Screenshots: `docs/phase5/`.

## Next step (Phase 6, run in the master: small steps)
1. DONE by master at `5b6db77`: pytest 105, innerHTML none, safety.py diff empty, runbook copies match. Branch pushed. Preview: https://runbookpilot-54xmbz191-daddy-ousen-s-projects.vercel.app (Vercel Deployment Protection: needs Vercel login or a Share link). Static files checked 200. Waiting: owner phone test + review, then merge.
   - Gotcha: in Git Bash, `vercel curl /path` needs `MSYS_NO_PATHCONV=1`. `vercel curl` adds `.vercel` to `.gitignore`: revert it.
2. Lighthouse again (see command below) on `/#triage`; it needs a score >= 95. Optional: also run it on `/#runbooks`, `/#safety`, `/#benchmark`, `/#integrations`.
3. 390 px check on the Vercel preview; real phone test (owner or a phone browser).
4. Vercel preview of the branch (`vercel` CLI 54.x is installed globally; Vercel env vars `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` must exist for the project). Check `/static/css/*`, `/static/js/**`, `/static/favicon.svg`, `/static/runbooks/*.md` and `index.json` all return 200 there (`vercel.json` `includeFiles` is `static/**`), and that the page's hash routes load.
5. Owner reviews the preview. Then merge `ui-redesign` to main (owner says go). Do not push before the owner agrees.
6. Then stop UI work (Nov 4, 12:00 Dhaka) and record the demo video.

## Open items / limits (none block Phase 6)
- Lighthouse sees only the empty state. The result state was checked with axe-core.
- 21 Tab stops from the ticket box to Run demo (Run demo is after the input column in DOM order).
- At 390 the index status shows a dot only.
- Integrations header badge repeats the banner line under it.
- No `og:image` (needs an absolute URL).
- Backend (report only): see "Backend issues seen in Phase 5" in `progress.md`.

## Commands
- Server: `OPENBLAS_NUM_THREADS=1 .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010`. Port 8000 has a stale old server. Stop 8010 by PID (`Get-NetTCPConnection -LocalPort 8010`).
- Lighthouse (works with Edge, not Chrome): `$env:CHROME_PATH="C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"; npx --yes lighthouse@12 "http://127.0.0.1:8010/#triage" --only-categories=accessibility --chrome-flags="--headless=new --disable-gpu --no-first-run" --max-wait-for-load=45000 --output=json --output-path=lh.json --quiet`. Run it from a temp folder, not the repo.
- Headless Edge over CDP (Node 24, built-in `WebSocket`): launch `msedge.exe --headless=new --remote-debugging-port=N --user-data-dir=<tmp>`, then `Emulation.setEmulatedMedia`, `Emulation.setDeviceMetricsOverride`, `Input.dispatchMouseEvent`, `Page.captureScreenshot`. Good for dark mode, reduced motion, real clipboard (`Browser.grantPermissions`) and screenshots.
- A stored result shows a triage result without an LLM call: in the page, `sessionStorage.setItem("rbp_last_result", JSON.stringify({data, meta, ticket}))`, then reload. `meta` = `{requestId, metaModel, reasoningMode, safetyOverrides, bm25Scores, elapsedSeconds, vision, rmmLoop}`.

## Gotchas
- Keep these IDs in `index.html` (UI tests check them as text): `nav-tab-triage`, `nav-tab-integrations`, `nav-tab-eval`, `eval-workspace`, `integrations-workspace`, `reasoning-mode-select`, `screenshot-file-input`, `btn-sample-shot-rdp`, `btn-sample-shot-vss`, `rmm-loop-bar`, `btn-draft-runbook`, `btn-hot-index-runbook`, `safety-inspect-form`, `integration-provider-list`, `integration-config-form`, `cfg-fields-grid`, `cfg-webhook-url`, `cfg-test-btn`, `cfg-save-btn`, `pending-queue-panel`, `pending-queue-list`, `rmm-telemetry-panel`, `psa-writeback-panel`, `ticket-input`, `loading-state`, `escalate-banner`, `approval-warning-banner`, `likely-cause-text`, `confidence-badge`, `matched-runbooks-list`, `steps-list`, `commands-list`, `theme-toggle`.
- In `result.js`, resolve template slots BEFORE `container.appendChild(root)`.
- CSS order: `components.css` loads after `layout.css`. A layout rule that hides a `.btn` or `.badge` needs a stronger selector.
- SVG has no `.hidden` property. Use `toggleAttribute("hidden", ...)`.
- The browser caches `/static/*` and `/`. After edits: `await fetch(url, {cache: 'reload'})` for each changed file (and `/` for `index.html`), then `location.reload()`.
- The built-in browser's screenshots often show the frame BEFORE the last change (take a second one). Its clipboard is blocked.
- Triage is a live LLM, 6 to 33 s. Upstream 504 hit 3 of 6 calls in Phase 3, 0 of 4 since.
- Git autocrlf warns on edited files (LF becomes CRLF). Harmless. Files in the working tree are LF.
- `.env` holds the real LLM key. Never print or commit it.

## Active files
- `static/index.html`, `static/css/{components,views,tokens}.css`, `static/js/{theme}.js`, `static/js/views/{triage,result}.js`, `static/favicon.svg`, `README.md`, `progress.md`, `handoff.md`, `docs/phase5/`.
