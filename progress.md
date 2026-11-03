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
- [ ] Phase 3: Triage view (plan section 6, all states). **Checkpoint: all samples, uncovered, screenshot, RMM re-triage.**
- [ ] Phase 4: Runbooks, Safety lab, Benchmark, Integrations views.
- [ ] Phase 5: Polish (responsive, a11y, copy, meta, favicon).
- [ ] Phase 6: Verify (pytest, innerHTML grep, safety.py diff empty, Lighthouse a11y >= 95, 390 px, keyboard, Vercel preview, owner review, merge).

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
- LLM paired step "Clear cached credentials" with `Clear-RecycleBin -Confirm` (lockout sample). Wrong command, label is right.
- A stale server (PID 3952) holds port 8000: old code, no `/integrations/queue`, rejects triage with "Extra inputs are not permitted". Kill it before demos.
- `.venv` start gave an OpenBLAS memory error. `OPENBLAS_NUM_THREADS=1` fixes it.
- Triage latency now 10 to 33 s (Deep + screenshot 33 s). Slower than the 5 to 11 s seen in Phase 0.
- System `python` has no app packages (`rank_bm25` missing). Run the server with `.venv/Scripts/python.exe`.
- Python Playwright now fails on this machine: Node driver "JavaScript heap out of memory" at launch, also outside the sandbox. The built-in browser pane works.
- The built-in browser denies `navigator.clipboard.writeText`. The UI now falls back to `execCommand("copy")`.
- Error bodies are raw `{"detail": ...}`; no `retry_after` in the body. But 429 sends a `Retry-After` header (`app/main.py:262`), so the UI can show a wait time. Latency 5 to 11 s, no real stages.
