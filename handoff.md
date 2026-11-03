# Handoff

## Current state
- UI redesign is DONE and LIVE. `ui-redesign` merged into main (fast-forward, `58e7b73` + this docs commit). Pushed.
- Production: https://runbookpilot.rhasan.online (alias https://runbookpilot-phi.vercel.app). Checked: page, CSS, JS, favicon, runbook files, `/runbooks` all 200.
- Tag `pre-redesign` (`d5fb9d5`) marks the old UI. To roll back: revert to it on a branch, test, then merge.
- Checks on main: pytest 105 passed; no innerHTML in `static/`; `app/safety.py` unchanged; Lighthouse a11y 100 (Phase 5).

## Next step
- Record the demo video, then submit (due Nov 5, 08:00 Dhaka). Use Standard mode: Deep + screenshot can take 30 s.
- Demo path: open `/#triage`, click "Run demo", show verdict strip, steps, command blocks, Copy; then Uncovered VoIP sample (escalate); then Safety lab.

## Open owner choices
- `Clear-RecycleBin -Confirm` is a wrong command in `data/runbooks/02_ad_account_locked.md:22` (and `static/runbooks/02_ad_account_locked.md`). It shows in the AD lockout demo.
- Vercel CLI made a protection bypass token for the project. Delete it in Vercel if not wanted.

## Gotchas
- `.env` holds the real LLM key. Never print or commit it.
- Local: port 8000 has a stale old server (PID 3952). Run on 8010: `OPENBLAS_NUM_THREADS=1 .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010`.
- The LLM endpoint sometimes returns 504 (seen on 3 of 6 calls in Phase 3). The UI shows "Try again".
- Git Bash: `vercel curl /path` needs `MSYS_NO_PATHCONV=1`; it also edits `.gitignore` (revert it).
- `static/runbooks/` must stay byte-equal to `data/runbooks/` (only `index.json` extra).
