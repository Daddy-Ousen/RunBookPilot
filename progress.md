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
  - Known gaps (closed in Phase 5): hint-line links and `.btn-sm` are 40 px now; `prefers-reduced-motion` and the real clipboard were checked in headless Edge; Lighthouse ran (100). The built-in browser still blocks the clipboard, so webhook Copy shows "Select and copy" there.
- [x] Phase 5: Polish (responsive, a11y, copy, meta, favicon). Done 2026-11-03 (commits `61f1936`, `c4be2ef`, `d04ec9e`, then a docs commit). **Checkpoint: owner can review; Phase 6 follows.**
  - [x] Lighthouse runs on this machine with Edge, not Chrome. Command: set `CHROME_PATH` to `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`, then `npx lighthouse@12 "http://127.0.0.1:8010/#triage" --only-categories=accessibility --chrome-flags="--headless=new --disable-gpu --no-first-run"`. Chrome (`C:\Program Files\Google\Chrome`) failed with PROTOCOL_TIMEOUT. Score 100 (Lighthouse 12.8.2, Edge 156) in the mobile profile, and 100 in the desktop profile with a dark-mode Chrome flag (the flag effect was not checked; axe below covers dark). No failed audits. Lighthouse sees the empty state only.
  - [x] axe-core 4.10 (the engine inside Lighthouse; tags wcag2a, 2aa, 21a, 21aa, 22aa and best-practice) on all 5 routes, light and dark (emulated media), with a mocked result on screen and all `<details>` open: 0 violations.
  - [x] Targets: `.btn-sm` is 40 px at every width now. New `.link-target` class (40 px) for the triage hint links, "All runbooks" and "Open in Runbooks". The hint line is "Next:" plus two link buttons ("Try the uncovered VoIP sample", "Test a command in the Safety lab"). Measured at 1440, 1024, 768 and 390 for all 5 routes (all `<details>` open): 0 targets under 40 px, 0 sideways scroll, 1 visible `<h1>` per view. 1024 was walked for the first time: 64 px icon rail, 2 columns, clean.
  - [x] Layout shift: 0 when the result arrives (1440 and 390, mocked `/triage` with a 2 s delay). One 0.28 shift at 390 when Run demo starts: the Samples panel collapses on the user's own click (by design from Phase 3).
  - [x] `prefers-reduced-motion`: emulated in headless Edge (CDP). With "reduce": transitions 0 s, skeleton animation none, `--dur-med` 0 ms. With "no-preference": 0.12 s, shimmer, 180 ms.
  - [x] Copy with the real clipboard: headless Edge, clipboard permission granted, real mouse click: button shows "Copied", `navigator.clipboard.readText()` equals the command, live region says "Command copied". The built-in browser still blocks the clipboard (fallback path shows "Copied" through `execCommand`).
  - [x] Keyboard-only run (built-in browser, real keys, live Run demo 13.5 s): skip link (Enter focuses `#main`); Tab order ticket, Clear, Analyze, Mode, Attach, 2 sample-screenshot buttons, 5 samples, 2 queue tools, 6 queue rows, Run demo (21 stops); Enter on Run demo. Then (mocked reply) Ctrl+Enter, focus moves to the verdict strip, hint links, Space ticks step 1 (saved), Enter on Copy ("Copied", "Command copied"), Stage buttons, RMM box, Enter opens 2 source runbooks (text loads, the text box is focusable, "Open in Runbooks" link), Enter opens Details, Send to select, Enter on Post internal note ("Note posted (staged)" toast and notice). The 2 px focus ring shows on every stop.
  - [x] A11y changes: focus moves to the verdict strip when a result arrives, and to the error panel when a request fails (tabindex -1; the next Tab reaches Try again). On desktop the Samples and Queue headers have `tabindex=-1` and `aria-disabled` (they cannot collapse there). Roles checked: `role=status` on result status and index status, `role=alert` on error panels and field errors, `aria-live` on loading line, steps count and Copy text.
  - [x] Contrast spot check (script): the smallest text pairs (text-2 and text-3 on bg, surface, surface-2; risk text on risk bg; on-accent; ink-muted; line-strong as a 3:1 UI pair) all pass in light and dark (lowest: text-3 on surface-2 light 5.16, line-strong light 3.45).
  - [x] Copy pass (all 5 views, empty and result states): terms already matched the design-plan section 8 map. Changed: sample screenshot buttons "RDP error" and "VSS error" became "Attach RDP sample" and "Attach VSS sample" under the line "Or try a sample screenshot:" (stacked, no ugly wrap in the narrow column); hint line wording. Toasts reuse the button words. Raw API terms only in Details, Technical details and the Safety lab technical details.
  - [x] Head: `<title>` ("Triage · RunbookPilot"; the router changes it per view), `<meta description>` (160 chars), `og:type`, `og:site_name`, `og:title`, `og:description`, `theme-color` for light (`#f5f6f8`) and dark (`#0e1014`) by media query; `theme.js` sets both to the chosen theme when the user toggles. Favicon is `static/favicon.svg`: cobalt `#2b4acb` rounded square with a white `>_` prompt. Checked on a light and a dark tab strip (`docs/phase5/favicon-light-dark.png`); served 200 `image/svg+xml`. No `og:image` (needs an absolute URL; not added).
  - [x] Decoration removed: the skeleton shimmer (an endless gradient animation on the loading blocks; plan section 4 says no gradient decoration and motion only for user actions). The skeleton is still blocks now; the elapsed timer shows that work is going on. Token `--skeleton-b` removed.
  - [x] README: new "User interface" section (routes, triage flow, Run demo, Sample data and Staged labels, errors); stale button names and `/#eval` fixed.
  - [x] Checks: pytest 105 passed; `git grep innerHTML -- static` none; `git diff pre-redesign -- app/safety.py` empty; `diff -r data/runbooks static/runbooks` only `index.json`; no diff in `app/ tests/ data/` since `5772291`. 2 live triage calls: Run demo 200 (13.5 s), Uncovered VoIP 200 (6.0 s, escalate, "No runbook covers this ticket"). Server stopped, tab closed.
  - Screenshots: `docs/phase5/` (`triage-result-1024.png`, `triage-result-390.png`, `empty-dark-1440.png`, `empty-dark-390.png`, `favicon-light-dark.png`; made with headless Edge and CDP; the result comes from a stored mock).
  - Not done or limits: Lighthouse sees the empty state only, and the dark flag is unverified there (axe covers the result state and dark). Phone test and Vercel preview are Phase 6. The built-in browser cannot show the tab strip, so the favicon proof is a mock tab strip. Keyboard users need 21 Tab stops from the ticket box to Run demo (Run demo sits after the input column in DOM order; changing DOM order would break the visual order, so it stays). At 390 the index status shows a dot only (the text is hidden). The Integrations header badge "Staged, not live" repeats the banner under it (left in).
- [x] Phase 6: Verify (done 2026-11-03; merged to main) (`static/runbooks/` matches `data/runbooks/`, pytest, innerHTML grep, safety.py diff empty, Lighthouse a11y >= 95, 390 px, keyboard, Vercel preview, owner review, merge).
  - [x] Master re-ran local checks 2026-11-03 at `5b6db77`: pytest 105 passed; no innerHTML/outerHTML/insertAdjacentHTML in `static/`; `git diff pre-redesign -- app/safety.py` empty; `diff -r data/runbooks static/runbooks` only `index.json`; no diff in `app/ data/ tests/` since `pre-redesign`.
  - [x] Lighthouse a11y 100 on `/#triage` (Phase 5, Edge). 0 sideways scroll at 390. Keyboard-only triage run passed (Phase 5).
  - [x] Pushed `ui-redesign` to origin (owner OK, 2026-11-03). Vercel preview Ready: https://runbookpilot-54xmbz191-daddy-ousen-s-projects.vercel.app (Vercel login required). Master checked via `vercel curl`: `/`, CSS, JS modules, favicon, `static/runbooks/*` and `/runbooks` all 200 with correct types.
  - [x] Owner approved the preview (phone test by owner).
  - [x] Merged `ui-redesign` into main (fast-forward to `58e7b73`), pytest 105 on main, pushed. Production deploy Ready at https://runbookpilot.rhasan.online (also https://runbookpilot-phi.vercel.app): `/`, CSS, JS, favicon, runbooks all 200; title "Triage · RunbookPilot".

## Phase 7 (2026-11-04): Mood refresh (DONE, live)
- Owner said the live site looks "bland and depressing".
- [x] 3 mood mockups on a design canvas (not in the repo): https://claude.ai/artifact/EzfKvysv39heCk4zjBQsoL. A = Midnight Console (dark first, cyan accent, IBM Plex Sans). B = Friendly Daylight (lavender ground, violet accent, rounded, pill nav, hero input, Manrope). C = Signal Blocks (filled cobalt rail, full-width amber verdict banner, Space Grotesk). All show the same AD lockout result.
- [x] Owner picked B: Friendly Daylight (2026-11-04).
- Model guide: Phase 7 = Opus 5.5, high (sub-session on branch `ui-mood`).
- [x] Applied B on branch `ui-mood` (2026-11-04, sub-session, `27135d0`).
- [x] Master checked: pytest 105 on main; no diff in `app/ data/ tests/`; `app/safety.py` unchanged vs `pre-redesign`; no innerHTML in `static/`; screenshots match B.
- [x] Owner chose to merge without a preview. Fast-forward main to `27135d0`, pushed. Production checked: `/`, tokens.css (has `#5b3df5`), Manrope font link, `ps-highlight.js`, favicon, `/runbooks` all 200; hero renders in the browser.
- Not re-run: Lighthouse, axe, keyboard-only pass.
  - [x] Tokens (`static/css/tokens.css`, light + both dark blocks): lavender `#f4f2ff` ground, white surface, text `#1b1640`, violet accent `#5b3df5` / text `#4a2fe0` / tint `#ece8ff`; violet-tinted dark (`#120f24` bg, `#1a1633` surface, `#b5a6ff` accent text). New: `--r-pill`, `--r-input` 16, `--r-panel` 20, `--r-card` 24, `--shadow-card`, `--shadow-soft`, `--ro-solid`/`--ro-row`, `--na-ink`/`--na-sub`/`--na-line`, `--esc-ink`, 5 sample tints, 4 code colors.
  - [x] Font: Manrope 400-800 + JetBrains Mono via the same Google Fonts `<link>` (Geist removed). `theme-color` metas + `theme.js` bar colors = `#f4f2ff` / `#120f24`. Favicon violet `#5b3df5`; brand glyph uses it.
  - [x] Components: pill buttons (700 weight), pill badges, 16 px inputs (1.5 px `--line-strong` border kept for 3:1), segmented Mode = lavender track + white knob with violet ring, cards with soft shadow, tinted notices, rail active = solid violet pill at every width.
  - [x] Triage: input blocks are cards; samples are tinted tiles (5 hues); verdict = tinted card per state with a round icon (CSS background SVG), 28 px 800 title, white pill facts (meter inside the confidence pill); result sections are cards; steps have numbered circles (green `#12b886` + row tint when ticked; ticked text no longer struck through); command block = white card, pill risk tab, dark `#1b1640` code (16 px radius), dark Copy pill, amber border on needs-approval; writeback = violet tint card. "Not run by RunbookPilot." kept.
  - [x] Other 4 views: same tokens; Runbooks reader, Safety lab form and test list, Integrations detail sections and Benchmark table are cards. Checked at 1440 dark and 390 light/dark.
  - [x] Nice to have, done: (1) top pill nav at >= 1200 px, CSS only (the rail is `position: fixed` in the top bar; icons hidden; the model badge hides at 1200-1599 and stays in result Details). Below 1200 the icon rail and the menu sheet are unchanged. (2) Hero line "Paste a ticket. Get a safe fix plan in seconds." in the ticket card, only on the empty state (CSS `:has`). (3) PowerShell colors: `static/js/ps-highlight.js` builds `textContent` spans (cmdlet, param, string, variable, pipe); used in triage commands and the Safety lab. Copy still copies `cmd.command`.
  - [x] Checks: pytest 105 passed; `git grep innerHTML|outerHTML|insertAdjacentHTML -- static` 0; `git diff pre-redesign -- app/safety.py` empty; no diff in `app/ data/ tests/`; `diff -r --strip-trailing-cr data/runbooks static/runbooks` only `index.json` (plain `diff -r` shows CRLF-only noise in the working tree; git is clean). Contrast script (scratchpad): 64 pairs x light/dark = 128, 0 fail (lowest text pair: white on dark accent 5.12; lowest UI pair: line-strong on light bg 3.21).
  - [x] Browser (built-in, mocked `/triage`, no live LLM calls): 5 routes at 1440 and 390, light and dark: 0 sideways scroll (also 375), 0 targets under 40 px, 1 h1 per view, no all-caps, no text under 13 px, no console errors. 1200 (pill nav, no overlap) and 1024 (icon rail) checked. Needs approval, escalate, loading, ticked step, menu sheet checked.
  - Fix during the check: at 375-390 the bigger brand pushed the top bar 20-30 px too wide. Now the brand is smaller below 768 and the "· View" label hides below 440.
  - Screenshots: `docs/phase7/` (`empty-1440-light.jpg`, `result-1440-light.jpg`, `result-1440-dark.jpg`, `commands-1440-dark.jpg`, `escalate-1440-light.jpg`, `result-390-light.jpg`; built-in browser, 1440 shots scaled to 800 px wide).
  - Not done: Lighthouse and axe not re-run; keyboard-only pass not re-run (no DOM order change except the hero `<div>`, which has no focus stop). At >= 1200 the nav sits after the theme button in Tab order (DOM order) but shows in the middle of the bar. No Vercel preview yet.

## Next
- UI work is finished. Record the demo video (Standard mode; stop the stale server on port 8000 first if demoing locally). Submit by Nov 5, 08:00 Dhaka.
- Optional, owner choice: fix `Clear-RecycleBin -Confirm` at `data/runbooks/02_ad_account_locked.md:22` (and the copy in `static/runbooks/`).
- Optional: delete the Vercel protection bypass token the CLI made (Vercel > Settings > Deployment Protection).

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

## Backend issues seen in Phase 5 (report only)
- Integration descriptions from `GET /integrations` (`app/integrations.py`) use words such as "grounded" and "display-only PowerShell plans". The UI shows them as they are.
- `POST /safety/inspect` for the default test command (`Get-Service Spooler; Stop-Service Spooler -Force`) returns "Blocked: contains unquoted shell metacharacters..." with risk `needs_approval`. This is correct, but the UI headline "Changes the system. Needs approval." reads oddly for a command that was blocked and not judged as a change.
- Browsers ask for `/favicon.ico`; the app has no route for it (404 in the logs). The page uses `/static/favicon.svg`.
- Phase 6: check that Vercel serves `/static/css`, `/static/js`, `/static/favicon.svg` and `/static/runbooks`.

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
- Python Playwright now fails on this machine: Node driver "JavaScript heap out of memory" at launch, also outside the sandbox. The built-in browser pane works. Phase 5: headless Edge over CDP works (Node 24 has a built-in `WebSocket`, no extra package) and Lighthouse works with Edge (not Chrome). The scripts were in the session scratchpad, not in the repo.
- The built-in browser denies `navigator.clipboard.writeText`. The UI now falls back to `execCommand("copy")`.
- Error bodies are raw `{"detail": ...}`; no `retry_after` in the body. But 429 sends a `Retry-After` header (`app/main.py:262`), so the UI can show a wait time. Latency 5 to 11 s, no real stages.
