# Progress — RunbookPilot UI redesign

Source plan: `UI_REDESIGN_PLAN.md` (repo root). Follow it phase by phase. Stop at each checkpoint for the owner.

## Deadlines (Dhaka time)
- UI work stops: Nov 4, 12:00.
- Submission due: Nov 5, 08:00 (Nov 4, 9:00 PM ET).

## Setup (done)
- [x] Tag `pre-redesign` on main at `d5fb9d5`.
- [x] Branch `ui-redesign` created. All redesign work goes here. Main stays deployable.
- [x] `UI_REDESIGN_PLAN.md` copied to repo root.

## Phases
- [x] Phase 0: Audit (done 2026-11-03; `docs/ui-audit.md` + 21 PNG in `docs/audit/`). Screenshots at 1440/768/390 for every view. `docs/ui-audit.md` with 10 worst problems. **Checkpoint: show audit.**
- [x] Phase 1: Design plan (approved 2026-11-03 with 2 owner tweaks). `docs/design-plan.md`. **Checkpoint: wait for owner OK.**
  - [x] Draft written 2026-11-03 (`docs/design-plan.md`). Contrast pairs checked with a script: all AA, light and dark.
  - [x] Owner OK, with tweaks: (1) RMM re-triage stays visible below commands; (2) keep Google Fonts link, no self-hosted fonts.
- [x] Phase 2: Foundation (done 2026-11-03, commits `4b13760`..`fd5f989`). **Checkpoint: shell works, old features run.**
  - [x] `static/index.html` is the shell + `<template id="result-template">`. CSS in `static/css/{tokens,base,layout,components,views}.css`. JS ES modules in `static/js/{main,router,dom,api,copy,theme,toast,store,clipboard}.js` + `static/js/views/{triage,result,runbooks,safety,benchmark,integrations}.js`.
  - [x] Checks: pytest 105 passed; `git grep innerHTML -- static` 0 hits; `git diff pre-redesign -- app/safety.py` empty; all 5 routes at 1440 and 390, no console errors, no sideways scroll at 390; theme toggle light/dark.
  - [x] Old features run: Ctrl+Enter, samples, screenshot upload + 2 sample PNGs, Standard/Deep, queue + staged filter + link/unlink, RMM check staging, approval gate, RMM re-triage, writeback note + Tier 3 flag, draft runbook, add to index + re-run, safety lab, benchmark, integrations (fill demo, check, save, reset, webhook copy), `#eval` -> `#benchmark`, skip link, menu sheet (Esc closes).
  - [x] 4 live triage calls used: covered queue ticket (18 s), RMM re-triage (20 s), uncovered VoIP (10 s), VSS screenshot in Deep (33 s). Draft runbook live once (25 s). Hot-index re-run and 429 countdown tested with an in-page fetch mock.
  - Screenshots: `docs/phase2/*.jpg` (built-in browser; 1440 shots are scaled to 800 px wide).
- [x] Phase 3: Triage view (plan section 6, all states). Done 2026-11-03 (the 2 open live checks and the source runbook text were closed in Phase 4). **Checkpoint: all samples, uncovered, screenshot, RMM re-triage.**
  - Built 2026-11-03 (commits `2123b78`, `dbf73ea` and the copy-fix commit after them). NOT marked done: 2 live checkpoint items failed on the LLM upstream (see below).
  - [x] Input column: ticket box + counter + Analyze ticket, 5 samples as a described list (adds "RDP error screenshot"), drop zone with preview and Remove, Standard/Deep with one help line, queue as full list (provider, age, title, ref, status, priority) with "Sample data". Samples/Queue are `<details>`: forced open at >= 960 px, collapsed on mobile (Samples open on the empty state).
  - [x] Result order: verdict strip (state word, 3-segment neutral meter + word, runbook count, counts line), quiet hint line, likely cause, tickable steps (localStorage `rbp_ticks_<requestId>`), commands (read-only group, amber warning, needs-approval group), "Check results from RMM" box (Sample data) below commands, source runbooks as `<details>`, escalation panel, Details (collapsed), writeback bar with "Staged, not sent to a live PSA."
  - [x] Bold command block: solid risk tab (icon + word; amber tab has 1 px `--na` border), 4 px rail, ink code with `PS>` prompt, purpose line, Copy -> "Copied" 2 s + aria-live "Command copied" + rail pulse, "Not run by RunbookPilot." in every block, staged RMM button (needs-approval opens an approval-note drawer). Staged RMM output is appended to the RMM check box.
  - [x] States: empty (invite, Run demo, 3-line legend), loading (skeleton shaped like the result + timer, no stage names), errors 429 (Retry-After countdown), 504 / browser timeout (90 s), 502/500, 503, 422/400/413, network. Each: cause, next step, Try again, collapsed Technical details. An older result stays under an error, dimmed.
  - [x] Last result kept in sessionStorage, so a reload shows it again with its ticks. A new tab starts on the empty state (judges see Run demo).
  - [x] Escalate with a matched runbook (runbook rule says escalate) has its own sub-line and help text.
  - [x] Checks: pytest 105 passed; `git grep innerHTML -- static` 0 hits; `git diff pre-redesign -- app/safety.py` empty; no diff in `app/ data/ tests/`; all handoff IDs present.
  - [x] Browser (mocked `/triage`): covered, needs approval, escalate, every error type, Copy, ticks survive reload, RMM stage + approval gate, writeback note, draft -> add runbook -> re-run (mocked). 390 px: no sideways scroll, all targets >= 40 px. 768 px: same. Keyboard: Tab order skip link -> top bar -> rail -> ticket -> Clear -> Analyze; Ctrl+Enter; Space ticks; Enter on Copy and Details; focus ring visible.
  - [x] Live (6 calls): Run demo AD lockout 200 (12.8 s); VSS 502 (upstream 504), then Try again with VSS sample screenshot 200 (30.5 s, escalate by runbook rule); M365 mail 502 (upstream 504); RMM re-triage 502 (upstream 504, request accepted); Uncovered VoIP 200 (8.7 s, escalate).
  - [x] Live checks closed in Phase 4 (2 calls, same request shape as the UI sends): M365 mail covered sample 200 in 14.0 s (rb-04, high confidence, 5 commands); RMM re-triage with `rmm_diagnostic_output` 200 in 16.6 s (rb-02, high, 3 commands).
  - [x] Source runbook text: OWNER DECIDED 2026-11-03 option C. Done in Phase 4: `static/runbooks/*.md` (byte copy of `data/runbooks/`) + `static/runbooks/index.json` (ID to file). Source runbooks `<details>` load the text on first open. Phase 6 re-checks `diff -r data/runbooks static/runbooks` shows only `index.json`.
  - Not emulated: `prefers-reduced-motion` (CSS sets all durations to 0; not checked in the browser).
  - Screenshots: `docs/phase3/` (empty, loading, covered, needs approval, escalate, 429 error, 390 result, dark result).
- [x] Phase 4: Runbooks, Safety lab, Benchmark, Integrations views. Done 2026-11-03 (commits `66c3bc8`, `c7d84b6`, `256b66d` and the Integrations/fix commit after them). **Checkpoint: all 5 routes work at 1440/768/390, light and dark.**
  - [x] Source text: `static/js/markdown.js` (safe renderer: headings, paragraphs, lists, quotes, code fences, `inline code`, **bold**; createElement + textContent only; `parseFrontMatter`, `shortLine`), `static/js/runbook-text.js` (fetch + cache; session text first from `state.draftMarkdown`). Hot-indexed runbooks now also render through the renderer (same text).
  - [x] `#runbooks`: list (title, ID, short symptom line), search over title, ID, tags and full text, count line, reader (tags, rendered text, "Commands in a runbook are for a person to read and run. RunbookPilot never runs them."). Two panes at >= 960 px, list-or-reader with "All runbooks" back button below that. Badge "Added in this session" (draft) or "Added after setup" (listed but no static copy). Source runbooks have an "Open in Runbooks" link (`state.openRunbook`). Runbook text loads only after the view opens (no 18 file requests on the Triage page).
  - [x] `#safety`: result is a command-style block (risk tab + "Read-only" / "Changes the system. Needs approval." + reason + `PS>` command + "Not run. RunbookPilot never runs commands."). Raw `read_only`, `executed_on_host` and pipeline stages sit in collapsed "Technical details". `plainRisk()` in `copy.js` maps raw labels inside the API reason text. Error state has Try again. First open auto-checks the default command.
  - [x] `#benchmark`: two scorecards (Runbook search, Command safety) with plain labels, a "Pass" badge, a one-line description of the test, table stacks into rows at 390 px, BM25L only in the note under the table, loading and error (Try again) states, "Run the test again".
  - [x] `#integrations`: 12 connectors with count, "Staged, not live. Nothing is sent or received." banner, status words (Ready (staged) / Paused / Not set up), webhook help line, button help line, narrow screens scroll to the settings after a pick, load error has Try again. fill demo, check, save, reset and webhook copy all ran in the browser.
  - [x] Checks: pytest 105 passed; `git grep innerHTML -- static` 0 hits (also no outerHTML, insertAdjacentHTML, eval); `git diff pre-redesign -- app/safety.py` empty; no diff in `app/ data/ tests/`; `diff -r data/runbooks static/runbooks` shows only `index.json`; `index.json` IDs equal live `/runbooks` (18). 5 routes x 1440/768/390 x light/dark: no console errors, scrollWidth <= viewport (0 sideways scroll at 390), one h1 per view, no all-caps text, Tab shows the 2 px focus ring and Enter works on the Safety lab. Opened 3 runbooks in `#runbooks` (+ one from "Open in Runbooks") and a source runbook in a mocked triage result.
  - Screenshots: `docs/phase4/` (runbooks, safety, benchmark, integrations at 1440; runbooks list + reader and benchmark at 390; triage source runbook; safety dark 390).
  - Known gaps (small): Triage keeps some inline links 20 px high (hint line) and `.btn-sm` is 32 px on desktop (queue and sample-screenshot buttons; 40 px below 960 px). Phase 4 views use full-size buttons. `prefers-reduced-motion` not checked in the browser. Built-in browser blocks the clipboard, so webhook Copy shows "Select and copy". Lighthouse not run yet (Phase 6).
- [ ] Phase 5: Polish (responsive, a11y, copy, meta, favicon).
- [ ] Phase 6: Verify (`static/runbooks/` matches `data/runbooks/`, pytest, innerHTML grep, safety.py diff empty, Lighthouse a11y >= 95, 390 px, keyboard, Vercel preview, owner review, merge).

## Model guide (sub-sessions)
| Phase | Model | Effort |
|---|---|---|
| 0 Audit | Sonnet 5.5 | medium |
| 1 Design plan | Opus 5.5 | high |
| 2 Foundation | Opus 5.5 | high |
| 3 Triage view | Opus 5.5 | high |
| 4 Other views | Sonnet 5.5 | high |
| 5 Polish | Sonnet 5.5 | high |
| 6 Verify | Sonnet 5.5 | medium |

## Facts about the codebase
- FastAPI app: `app/main.py`. Run: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. Tests: `python -m pytest -v`.
- Frontend: single file `static/index.html` (4077 lines) at `pre-redesign`.
- Frontend since Phase 2: shell `static/index.html` + `static/css/*` + `static/js/*` (no build step). Static files are cached by the browser; force-reload after edits when testing.
- UI tests (`tests/test_hackathon_features.py`, `test_integrations.py`, `test_llm_and_api.py`) check old element IDs in `index.html`. Keep these IDs on the new elements (list in `handoff.md`).
- 18 runbooks in `data/runbooks`. Vercel `includeFiles` covers `static/**`, so `static/css` and `static/js` deploy.
- `innerHTML` hits at `pre-redesign`: 0.

## Hard rules (from plan section 2)
- No change to `app/safety.py`, API routes, or request/response shapes.
- UI never executes a command. `textContent` only for dynamic text.
- Label sample/staged data. No build step. No framework.

## Design decisions (Phase 1, approved)
- Keep hairline Geist look. Move to cool slate neutrals. Geist + Geist Mono via existing Google Fonts link (`display=swap`). No self-hosting.
- Brand accent: cobalt `#2b4acb` (light) / `#3d5ae0` fill, `#9aabff` text (dark). Red-orange removed (clashed with escalate red).
- Risk: teal read-only, amber needs approval, red escalate. Confidence and queue priority are neutral.
- 7-size type scale, 13 px floor. 4 px spacing base. 40 px targets. No shadows except toast/menu sheet.
- Rail: 216 px (>=1200), 64 px icons (768-1199), Menu sheet (<768). Routes `#triage #runbooks #safety #benchmark #integrations`; `#eval` redirects to `#benchmark`.
- File split: `static/css/{tokens,base,layout,components,views}.css`, `static/js/{main,router,dom,api,copy,theme,toast,store}.js` + `static/js/views/*.js`.

## Blockers
- None.

## Backend issues seen (report only, do not fix)
- Phase 4: 2 of 2 live triage calls gave 200 (14.0 s, 16.6 s). The 504s from Phase 3 did not come back.
- Phase 4: `POST /safety/inspect` puts raw `read_only` in the `reason` text ("Verified read_only: all 1 pipeline stage(s)..."). The UI maps it to "read-only". Backend text is unchanged.
- Phase 4: the webhook route `/integrations/webhooks/{id}` enqueues the event in the sample queue (`app/main.py:675`), not only a 202. The UI says "A test event sent to this URL gets a 202 answer (accepted). No live system is contacted."
- Git autocrlf is on: `git add` warns that LF becomes CRLF for `static/runbooks/*.md`. Both `data/runbooks` and `static/runbooks` follow the same rule, so `diff -r` stays clean in the working tree.
- Phase 3: Meta LLM endpoint returned HTTP 504 on 3 of 6 triage calls (backend maps it to 502 "Meta LLM endpoint returned HTTP 504."), after 4 to 15 s. Good calls took 8.7 to 30.5 s.
- `Clear-RecycleBin -Confirm` for "Clear cached credentials" comes from `data/runbooks/02_ad_account_locked.md` itself, not only from the LLM.
- No read-only route returns runbook body text. "Source runbooks" cannot show the runbook text without a backend or static-data change.
- The LLM can set `escalate: true` with matched runbooks and commands (runbook escalation rule, VSS + SqlServerWriter). The UI now handles this.
- LLM paired step "Clear cached credentials" with `Clear-RecycleBin -Confirm` (lockout sample). Wrong command, label is right.
- A stale server (PID 3952) holds port 8000: old code, no `/integrations/queue`, rejects triage with "Extra inputs are not permitted". Kill it before demos.
- `.venv` start gave an OpenBLAS memory error. `OPENBLAS_NUM_THREADS=1` fixes it.
- Triage latency now 10 to 33 s (Deep + screenshot 33 s). Slower than the 5 to 11 s seen in Phase 0.
- System `python` has no app packages (`rank_bm25` missing). Run the server with `.venv/Scripts/python.exe`.
- Python Playwright now fails on this machine: Node driver "JavaScript heap out of memory" at launch, also outside the sandbox. The built-in browser pane works.
- The built-in browser denies `navigator.clipboard.writeText`. The UI now falls back to `execCommand("copy")`.
- Error bodies are raw `{"detail": ...}`; no `retry_after` in the body. But 429 sends a `Retry-After` header (`app/main.py:262`), so the UI can show a wait time. Latency 5 to 11 s, no real stages.
