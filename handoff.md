# Handoff

## Baseten switch (DONE, live, 2026-11-04)
- Hackathon gives Baseten credits for Muse Spark Open. Base URL `https://inference.baseten.co/v1`. Model must be exactly `meta-models/muse-spark-open-1026` (key works only with it). Model passes the Meta-only check in `app/llm.py`.
- Local `.env` already switched; old Meta values are commented lines in `.env`. A backup of the old `.env` was copied to `%TEMP%/rbp_env_backup`.
- Owner pasted the real Baseten key into `.env`. Never print it.
- Model always reasons (default `xhigh`, slow). `LLM_REASONING_EFFORT=medium` set. Baseten returns reasoning in `reasoning_content`; `content` holds the answer, so the JSON parse should work. Verified locally: smoke test 1.6 s; 3 real triages correct in 2.8 to 6.1 s.
- Live site uses Baseten (checked with the `X-Meta-Model` response header). 3 live triages correct in 2.8 to 5.3 s.
- `LLM_REASONING_EFFORT` is set for Production only, not Preview.
- Next: record the demo video and submit (see Next step below).

## Current state
- main = Phase 0-6 redesign + Phase 7 "Friendly Daylight" reskin (`27135d0`), LIVE at https://runbookpilot.rhasan.online (alias https://runbookpilot-phi.vercel.app). Tag `pre-redesign` (`d5fb9d5`) marks the old UI; `7533855` is the last commit before Phase 7 (roll back the look by reverting `27135d0`).
- Mockup canvas: https://claude.ai/artifact/EzfKvysv39heCk4zjBQsoL (`project/Daylight.dc.html`). Branch `ui-mood` is merged (local only).
- Checks (sub-session on `ui-mood`, master re-ran pytest and rule checks on main): pytest 105 passed; no innerHTML/outerHTML/insertAdjacentHTML in `static/`; `app/safety.py` unchanged vs `pre-redesign`; no diff in `app/ data/ tests/`; contrast script 128 pairs AA (light + dark); 5 routes at 1440 and 390, light and dark: no sideways scroll, no target under 40 px, no console errors (mocked `/triage`).
- Screenshots: `docs/phase7/`.
- Theme: light is the default for everyone, also when the system is dark. Dark only by the theme button (stored in localStorage `rbp_theme`). Dark tokens live only in `:root[data-theme="dark"]` in `static/css/tokens.css`.

## What Phase 7 changed (files)
- `static/css/tokens.css`: new palette, radii (`--r-pill`, `--r-input`, `--r-panel`, `--r-card`), shadows, sample tints, code colors. Light + one dark block (`:root[data-theme="dark"]`).
- `static/css/base.css`, `components.css`, `layout.css`, `views.css`: the reskin. Top pill nav at >= 1200 px is CSS only (layout.css, `@media (min-width: 1200px)`).
- `static/index.html`: Manrope + JetBrains Mono font link, `theme-color` values, hero `<div class="hero">` in the ticket card. `static/js/theme.js`: bar colors. `static/favicon.svg`: violet.
- New `static/js/ps-highlight.js` (PowerShell color spans, textContent only). Used by `views/result.js` and `views/safety.js`.

## Next step
1. Record the demo video and submit (due Nov 5, 08:00 Dhaka). Demo path: `/#triage`, Run demo, verdict, steps, commands, Copy; Uncovered VoIP sample (escalate); Safety lab.

## Not done in Phase 7
- Lighthouse / axe not re-run. Keyboard-only pass not re-run.
- At >= 1200 px the pill nav is after the theme button in Tab order (DOM order), but it shows in the middle of the bar.
- The model badge hides at 1200-1599 px (the model name is still in result Details).
- The empty state now has two "Paste a ticket" lines (hero in the ticket card + empty card title). Copy left as it was.

## Open owner choices
- `Clear-RecycleBin -Confirm` is a wrong command in `data/runbooks/02_ad_account_locked.md:22` (and `static/runbooks/02_ad_account_locked.md`). It shows in the AD lockout demo.
- Vercel CLI made a protection bypass token for the project. Delete it in Vercel if not wanted.

## Gotchas
- `.env` holds the real LLM key. Never print or commit it.
- Local: port 8000 has a stale old server (PID 3952). Run on 8010: `OPENBLAS_NUM_THREADS=1 .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010`.
- The built-in browser caches ES modules. After JS edits, `fetch(path, {cache: "reload"})` each changed module, then reload.
- The LLM endpoint sometimes returns 504. The UI shows "Try again".
- Git Bash: `vercel curl /path` needs `MSYS_NO_PATHCONV=1`; it also edits `.gitignore` (revert it).
- `static/runbooks/` must stay equal to `data/runbooks/` (only `index.json` extra). Use `diff -r --strip-trailing-cr` (CRLF noise in the working tree).
