# RunbookPilot UI/UX Redesign Plan (for Claude Code)

Put this file in the repo root. Tell Claude Code: "Read UI_REDESIGN_PLAN.md and follow it phase by phase. Stop at each checkpoint."

Deadline: submission is due Nov 5, 08:00 Dhaka time (Nov 4, 9:00 PM ET). UI work must stop by Nov 4, 12:00 Dhaka time. Then record the demo video and submit.

---

## 1. What exists today

- FastAPI backend in `app/`. Static frontend in `static/index.html`. Runbooks in `data/`. Tests in `tests/`. Eval in `scripts/eval.py`. Deployed on Vercel (`vercel.json`).
- The user is an L2 IT support engineer at an MSP. The product helps a technician triage a Windows or M365 ticket.
- One long page holds all of this: ticket input, PSA/RMM queue, result, 12 integration connectors, a PowerShell safety sandbox, and a benchmark table.
- The top bar shows system terms ("Triage", "Integrations 0/12", "Safety & Eval 100%", "Index loading...").
- Raw API terms show in the UI: `read_only`, `needs_approval`, `executed_on_host: false`, "BM25L", "Hot-index".

The owner says the UI feels rudimentary. Verify this yourself with screenshots in Phase 0. Do not trust this text only.

## 2. Hard rules (do not break)

1. Do not change `app/safety.py`. Do not change any API route, request, or response shape.
2. The UI never executes a command. Keep the "never executed" message visible near every command.
3. Render all dynamic text with `textContent`. Never use `innerHTML` with API or user data. Run `git grep -n "innerHTML"` at the end. Each hit must be static markup only.
4. Label simulated data clearly. RMM device telemetry, connector status, and PSA queue items are samples or staged. Show a "Sample data" or "Staged, not live" label. Never present them as live customer data.
5. No new backend features. No new runtime dependency that needs a build server.
6. Keep the app a static frontend with no build step. Split `index.html` into `static/css/*.css` and `static/js/*.js` (ES modules). Do not move to React or another framework. Time is too short.
7. Work on branch `ui-redesign`. Before you start, tag the current main: `git tag pre-redesign`. Merge to main only after Phase 6 passes. Main must stay deployable at all times.
8. All existing flows must still work: Ctrl+Enter, quick samples, screenshot attach, Standard/Deep mode, RMM output re-triage, PSA writeback, draft runbook, hot-index, safety sandbox, benchmark.

## 3. Design goal

One job: a technician pastes or selects a ticket and gets a safe, clear fix plan in under 10 seconds of reading.

The product is a work tool. It is not a marketing page. The first screen is the workbench. Show a working state, not a hero banner.

Judges will spend 2 to 3 minutes. The first screen must show what the product does. A one-click demo must work.

## 4. Design direction (propose, then review)

Follow the `frontend-design` skill process: write a compact design plan first, review it against this brief, then build.

Starting points (change them if you can justify it):

- **Mood:** calm, precise, dense but easy to read. Like a good ticketing tool or a code review tool. Not a landing page.
- **Layout:** left rail for navigation. Main area has two columns on desktop: ticket and queue on the left, result on the right. Single column on mobile.
- **Color:** a cool neutral base. Colors carry meaning in this product. Use them only for meaning:
  - Read-only command: green-teal.
  - Needs approval: amber.
  - Escalate: red.
  - Confidence: a neutral scale, not red/green.
  - One brand accent for primary actions only.
- **Avoid these defaults:** cream background with terracotta accent; near-black with acid green; identical rounded cards with the same soft shadow; all-caps tracked labels above every heading; arrows on every button; gradient decoration.
- **Type:** one clear sans family for UI. One monospace family for commands, event IDs, and hex codes only. Set a real type scale. Keep lines under 80 characters.
- **Theme:** light and dark. Follow the system setting by default. The existing toggle stays. Check contrast in both.
- **Motion:** only for user actions (expand, copy, run). One calm state change when a result arrives. Respect `prefers-reduced-motion`.
- **Be bold in one place:** the command block with its risk badge. That is the memorable part of the product. Keep everything else quiet.

## 5. Information architecture

Move secondary tools out of the main page. Use hash routes (some exist already).

| Route | View | Contents |
|---|---|---|
| `/#triage` (default) | Triage | Queue, ticket input, result |
| `/#runbooks` | Runbooks | List of the 18 runbooks, search box, open one to read it |
| `/#safety` | Safety lab | The PowerShell sandbox |
| `/#benchmark` | Benchmark | Retrieval and safety scorecard |
| `/#integrations` | Integrations | The 12 connectors, marked "Staged, not live" |

Top bar: product name, model badge, index status (loaded / loading / error), theme toggle. Remove "Integrations 0/12" from the top bar.

## 6. Triage view: required changes

**Input area**

- A large ticket box with a character counter and a clear primary button "Analyze ticket".
- Quick samples as a compact list with a short title and one-line description. Not loose chips.
- Screenshot attach: a drop zone with preview and a remove button.
- Mode switch (Standard / Deep) with one line that explains the difference.
- The queue is a list with provider, title, age, and status. Selecting an item fills the ticket box.

**Result area** (in this order)

1. **Verdict strip:** confidence, matched runbook count, and one clear state: "Covered by runbooks", "Needs approval steps", or "Escalate to Tier 3".
2. **Diagnosis:** likely cause in plain words.
3. **Steps:** an ordered checklist. The technician can tick each step. Ticks stay in the browser only.
4. **Commands:** group by risk. Read-only commands first, then needs-approval commands. Each command has: monospace block, one-line purpose, risk badge with a text label (not color only), a copy button with a "Copied" confirmation. A needs-approval group has a clear warning above it.
5. **Matched runbooks:** a short list. Each item expands to show the source runbook text. This proves the answer is grounded.
6. **Escalation:** if `escalate=true`, show a clear panel with the reason and the two actions (draft runbook, flag Tier 3).
7. **Details (collapsed by default):** RMM telemetry, request ID, model, reasoning mode, BM25 scores, safety overrides. Technical terms live here only.
8. **Writeback bar:** PSA target, "Post internal note", "Flag for Tier 3". Label it "Staged, not sent to a live PSA".

**States (all required)**

- Empty: invite the user to try a sample ticket. Show one primary button "Run a sample ticket".
- Loading: skeleton of the result layout plus an elapsed timer. Do not fake stage names unless the backend sends real stages.
- Error: say what failed and what to do. Offer "Try again". Cover: rate limit (429), timeout, model error, bad input.
- Rate limit: show how long to wait if the response gives it.

## 6a. Words (copy)

- Use plain words. Sentence case. Active voice.
- `read_only` shows as "Read-only". `needs_approval` shows as "Changes the system. Needs approval."
- "Hot-index runbook & re-analyze ticket" becomes "Add this runbook and re-run triage".
- "BM25L" appears only in Details.
- A button says what it does. A toast uses the same word as the button.
- No filler, no marketing words.

## 7. Quality floor

- Responsive at 1440, 1024, 768, and 390 px. No horizontal scroll at 390 px.
- Keyboard: every control reachable, visible focus ring, logical tab order. Skip link stays.
- Screen reader: real buttons, labels, `aria-live` for the result and errors, risk badges have text.
- Contrast: WCAG AA in light and dark.
- `prefers-reduced-motion` respected.
- Touch targets at least 40 px.
- Fast: no layout shift when the result loads. Fonts self-hosted or loaded with `font-display: swap`.
- Favicon, page title, and social preview (`og:title`, `og:description`).

## 8. Demo path for judges

Add a visible "Run demo" button on the empty state. It loads a covered sample and runs triage. After the result, a short hint points to the Safety lab and the uncovered-ticket sample. Keep it unobtrusive. Do not add a modal tour.

## 9. Phases and checkpoints

**Phase 0: Audit (30 min).** Run the app. Take screenshots at 1440, 768, and 390 px for every view. Write `docs/ui-audit.md` with the 10 worst problems. Checkpoint: show the audit.

**Phase 1: Design plan (45 min).** Write `docs/design-plan.md` with: color tokens (4 to 6 named hex values plus the risk colors), type choices, spacing scale, layout wireframes in ASCII for desktop and mobile, and principles. Review it against section 4. Name one thing you changed after review and why. Checkpoint: wait for the owner's OK.

**Phase 2: Foundation (90 min).** Create the branch and tag. Split files. Add CSS tokens, light and dark themes, base components (button, badge, input, panel, toast), the app shell, the left rail, and the hash router. Checkpoint: the shell works and all old features still run.

**Phase 3: Triage view (3 to 4 h).** Build section 6 fully, with all states. Checkpoint: run all samples, the uncovered sample, the screenshot sample, and RMM re-triage.

**Phase 4: Other views (2 h).** Runbooks, Safety lab, Benchmark, Integrations. Same components.

**Phase 5: Polish (2 h).** Responsive, accessibility, copy pass, empty and error states, favicon and meta tags. Remove one decoration before you finish.

**Phase 6: Verify (1 h).**

1. `python -m pytest -v` passes.
2. `git grep -n "innerHTML"` shows only static markup.
3. `git diff pre-redesign -- app/safety.py` is empty.
4. Lighthouse accessibility score of 95 or more on `/#triage`.
5. No horizontal scroll at 390 px.
6. Keyboard-only run of the full triage flow works.
7. Deploy the branch as a Vercel preview. Test it on a real phone.
8. Owner reviews the preview. Then merge to main.

## 10. Out of scope (flag only, do not build)

- Backend changes, new connectors, auth, a database.
- Any change to how risk is classified.
- Report to the owner: any problem you see in the backend while you work.
