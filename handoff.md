# Handoff

## Now (2026-11-04)
- Local main = rewritten history (no Claude co-author lines) + model picker commit `2ae7f71`. Remote main is still the OLD history (`b22117a`). Force-push was blocked; owner must run it (see progress.md).
- Live site (Vercel from main) still shows the old badge until the push.
- Next: owner pushes, checks live picker and `klist purge` step, records the demo video (script in chat; due Nov 5 08:00 Dhaka), submits.

## Gotchas
- `.env` holds the real LLM key. Never print or commit it.
- Do not add `Co-Authored-By: Claude` lines to commits (owner removed them from GitHub on purpose).
- Local run: `OPENBLAS_NUM_THREADS=1 .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010`.
- The built-in browser caches ES modules: `fetch(path, {cache:"reload"})` then reload.
- `static/runbooks/` must equal `data/runbooks/` (+ `index.json`). Use `diff -r --strip-trailing-cr`.
