# RunbookPilot UI audit (Phase 0)

Date: 2026-11-03. Branch `ui-redesign`, from `pre-redesign` (`d5fb9d5`). No app code changed.
Method: Playwright (Python, Chromium) against a local server. Live LLM used 3 times (lockout sample at 3 widths) plus 1 uncovered sample (dark, 1440). 429 and 502 were simulated with route mocks.
Screenshots: `docs/audit/` (names below). All widths: 1440, 768, 390.

## Plan claims: verified

| Plan claim | Result |
|---|---|
| Top bar shows system terms | TRUE. Top bar text: `Triage`, `Integrations 0/12`, `Safety & Eval 100%`, `Meta Muse Spark 1.3`, `18 runbooks indexed`, `Display-only`, `Dark`. ([index.html:1728-1765](../static/index.html)) |
| Raw API terms in UI | TRUE. `read_only` and `needs_approval` show on badges, counters, banners ([index.html:2017](../static/index.html), [2924](../static/index.html)). `BM25L` on the empty state ([1908](../static/index.html)). `executed_on_host: false` in the Safety lab ([2196](../static/index.html)). `BM25 172.5` in the matched runbook chip. "Hot-index" on a button ([2007](../static/index.html)). |
| Horizontal scroll at 390 px | TRUE. `scrollWidth` is 584 px (triage), 540 px (integrations), 500 px (safety). No scroll at 768 and 1440. |
| Focus rings | OK. Global `:focus-visible` exists ([index.html:144](../static/index.html)). Measured: 2 px solid red-orange outline on a nav tab. |
| Contrast | Mostly OK. Failures (AA 4.5:1): the `/` separator in the brand (1.4:1 light, 1.55:1 dark), nav count chips (4.40 light, 3.74 dark), queue meta line (3.90 dark), item-count chips (4.09 dark). All are small mono text, 11 to 12 px. |
| Loading and error states | PARTLY. Loading: skeleton and timer exist, text is `Matching runbooks and validating triage response...` (generic, not backend stages). Error: plain red text banner. A 429 shows `Rate limit exceeded` and no wait time, though I sent `Retry-After: 30`. A 502 shows `upstream` raw. No "Try again" button. |
| Sample and staged data labelled | NO. The queue shows `CW #40821 / ConnectWise PSA / dc-01.corp.example.test` with `high` and `critical` and no "Sample" or "Staged" label. The only staged label is `status-staged` on the RMM badge (shows `NinjaOne RMM / online`) and the writeback has no "not sent" note. |
| No innerHTML | TRUE. `git grep innerHTML -- static` has 0 hits. |
| Page meta | Only `<title>` and a favicon. No `og:title`, no `og:description`. Fonts load from Google Fonts (`display=swap`, OK but external). |

## 10 worst problems (ranked)

1. **The 390 px layout breaks.** Where: top bar ([index.html:1728](../static/index.html), `.nav-tabs` at 981, `.topbar-controls` at 205). The model pill and the index label overlap the Triage/Integrations tabs, and "Safety & Eval" is clipped. The page scrolls sideways (584 px wide vs 390 px). Screenshots: `triage-empty-390.png`, `triage-result-390.png`, `integrations-390.png`, `safety-benchmark-390.png`. Hurts: a technician on a phone cannot use the tabs. A judge who opens it on a phone sees a broken page. Plan rule 7 (no horizontal scroll) fails.

2. **The result reads in the wrong order. The command, the thing to act on, is far down.** Where: `#result-container` ([index.html:1948-2053](../static/index.html)). Order today: request ID and model badges, PSA writeback panel, approval banner, diagnosis, steps, then commands. There is no verdict strip (covered / needs approval / escalate). Screenshot: `triage-result-1440.png` (commands start about 950 px down). Hurts: the technician must scroll past admin bars to find the fix. Judges cannot see the answer in 10 seconds.

3. **Raw API terms are the main labels.** Where: command badges and counter (`2 read_only, 2 needs_approval`, [index.html:2924](../static/index.html)), approval banner ([2017](../static/index.html)), empty state ([1908-1912](../static/index.html)), Safety lab ([2170](../static/index.html), [2196](../static/index.html)). Also `BM25 172.5` and `muse-spark-1.3 / standard` in the main flow. Screenshots: `triage-result-1440.png`, `triage-empty-1440.png`, `safety-benchmark-1440.png`. Hurts: it reads as a developer debug view, not a tool for an L2 tech. Judges see no plain language.

4. **Queue, sample, and RMM data is not labelled as sample or staged.** Where: queue panel ([index.html:1776-1790](../static/index.html)) and RMM telemetry ([1870-1896](../static/index.html)). Items look like live customer tickets, with `critical` and `high` tags and "online" status. Writeback bar has no "not sent to a live PSA" note. Screenshot: `queue-triage-top-1440.png`, `triage-result-1440.png`. Hurts: it can mislead a judge or a user into believing it is connected to a real PSA. Breaks plan rule 4.

5. **The empty state is a spec sheet, not an invitation.** Where: `#empty-state` ([index.html:1899-1923](../static/index.html)). It shows "No ticket loaded", two spec lines (BM25L, allowlist override) and an 18-row runbook list with truncated titles (`Failed BCDR Image Backup (VSS …`). There is no "Run demo" or "Run a sample ticket" button. Screenshot: `triage-empty-1440.png`. Hurts: a judge spends 2 to 3 minutes and the first screen does not show the product doing its job.

6. **Navigation is wrong for the job.** Where: top bar tabs ([index.html:1734-1746](../static/index.html)), views toggled by JS ([3791-3810](../static/index.html)). Only 3 views. "Safety & Eval" mixes two tools (sandbox and benchmark) in one view. There are `0/12` and `100%` count chips. No Runbooks view. Hash routes are `#integrations` and `#eval` only. Screenshots: `safety-benchmark-1440.png`, `integrations-1440.png`. Hurts: the "Integrations 0/12" chip looks like a failure on every screen. Judges cannot find the runbook source.

7. **The input column is crowded with equal-weight controls.** Where: `.pane-intake` ([index.html:1769-1863](../static/index.html)). One column holds the queue (clipped to 4 of 6 rows by `max-height: 215px`, [1363](../static/index.html)), 4 quick-sample chips, the mode select ("Meta mode:"), 3 screenshot buttons (Attach, Sample RDP PNG, Sample VSS PNG), then the textarea. Every control is the same small outlined button. Screenshots: `triage-empty-1440.png`, `queue-triage-top-1440.png`. Hurts: no clear first action. Samples have no description. The mode switch has no explanation. The queue hides 2 items with a nested scroll. Quick samples wrap to a lonely second line.

8. **The error, loading and rate-limit states are weak.** Where: `showError` ([index.html:2707](../static/index.html)), loading block ([1926-1945](../static/index.html)). Errors show raw server text only: `Rate limit exceeded`, `upstream`, `Extra inputs are not permitted (Request ID: …)`. No retry button, no wait time, no cause and next step. Loading says a generic sentence. Live latency was 5.5 to 11 s. Screenshots: `error-429-1440.png`, `triage-loading-1440.png`. Hurts: when the live LLM is rate limited during the judges' test, the app looks broken.

9. **Type is tiny and has no scale.** Where: global CSS. 24 different font sizes found on the empty screen. Many mono labels are 11.0 to 11.7 px (queue meta, chips, `BM25` score, counts). Mono is used for labels, chips and counters, not only for commands. Touch targets: 17 of 24 interactive items are under 40 px high at 1440 (28 of 35 with a result). Screenshots: `triage-empty-1440.png`, `triage-result-390.png`. Hurts: hard to read, hard to tap, fails contrast on several chips (see table). Plan section 7 floor fails.

10. **Command block has no step tick list, no "why" and no never-executed note beside each command.** Where: `#steps-list`, `#commands-list` ([index.html:2040](../static/index.html), [2050](../static/index.html)). Steps are a plain numbered list (not tickable). The "never executed" line is only under the ticket form ([1859](../static/index.html)), far from the commands. The command card header repeats the step sentence, then a green or amber `read_only` / `needs_approval` badge, `Queue RMM check` / `Request RMM change`, and `Copy` all in one row. Matched runbook chip shows an ID and a score but does not expand to the source text. Screenshot: `triage-result-1440.png`. Hurts: the product's best idea (safe command with risk badge) is not bold, and grounding is not provable.

Extra (not ranked): no `og:` meta tags; fonts come from Google Fonts; `Display-only` chip in the top bar is unclear; the dark theme works (`triage-empty-dark-1440.png`, `triage-uncovered-dark-1440.png`) but the brand `/` is almost invisible; the `Dark` toggle shows the next theme, not the current one.

## What works well (keep)

- Hairline, dense, calm look and the Geist type. No gradient decoration. Dark theme works and follows the system setting.
- Two-column desktop layout (input left, result right). No horizontal scroll at 768 and 1440.
- Command block: dark monospace block with `PS>` prompt, risk badge with text, Copy button. Read-only (green) and needs-approval (amber) colours carry meaning.
- Approval banner (amber) before commands, and the escalation banner for uncovered tickets (`triage-uncovered-dark-1440.png`: low confidence, no commands, clear reason).
- Visible focus ring (2 px), skip link, `role="alert"`, `aria-live` on result areas, `textContent` only (0 `innerHTML`).
- Skeleton loading with elapsed timer, char counter, Ctrl+Enter, Clear.
- Safety lab: fast, deterministic, shows parsed pipeline stages. Benchmark: 17/17 top-3 hit rate, 0 unsafe.
- Integrations view states "Standby mode (connectors staged, live polling inactive)" in a banner.

## Backend problems seen (report only, not fixed)

1. **Wrong command suggested.** Lockout sample, step 4 "Clear cached credentials or force logoff of stale sessions" was paired with `Clear-RecycleBin -Confirm` (marked `needs_approval`). This does not match the step. The LLM chose it (rb-02 runbook). Safety label is right, relevance is wrong. Hurts trust. The fix is in the prompt or the runbook, not the UI.
2. **Port 8000 had an old server running (PID 3952).** It had no `/integrations/queue` route (404) and rejected triage with `Extra inputs are not permitted`. It is a stale process from an older code version, not this branch. Check it before demos. I used port 8010 for the audit.
3. **OpenBLAS crash on start.** `.venv` start failed with `OpenBLAS error: Memory allocation still failed`. Setting `OPENBLAS_NUM_THREADS=1` fixed it. A judge or a Vercel build may hit the same on small hosts. Retrieval uses numpy (BM25).
4. **Error bodies are raw.** 429 and 5xx return `{"detail": "..."}` with no stable error code and no `retry_after` field in the body. The UI cannot show a wait time unless it reads the `Retry-After` header (check the 429 headers in `app/main.py`).
5. **Latency 5.5 to 11 s** per triage (live LLM). No streaming and no real stage events, so the loading state cannot show true stages.
6. **`Request: local` placeholder** shows in the result strip before the real request ID arrives (seen in the earlier broken run). Low risk.

## Notes for Phase 1

- Fix first, in order: mobile top bar (1), result order and verdict strip (2), copy (3), labels (4), demo empty state (5).
- Wide-element offenders at 390 px: `NAV.nav-tabs`, `#nav-tab-eval`, `.pane-intake`, `.pane-header`, `.corpus-row`.
- Screenshot list: `triage-empty-{1440,768,390}.png`, `triage-empty-dark-1440.png`, `triage-sample-filled-390.png`, `triage-loading-{1440,768,390}.png`, `triage-result-{1440,768,390}.png`, `triage-uncovered-dark-1440.png`, `queue-triage-top-1440.png`, `integrations-{1440,768,390}.png`, `safety-benchmark-{1440,768,390}.png` (Safety sandbox and Benchmark are one view today), `error-429-1440.png`, `focus-1440.png`.
- Full-page screenshots of sticky headers show overlap on tall pages (`triage-result-1440.png`). This is a capture artifact of the sticky top bar and pane headers, not a layout bug.
