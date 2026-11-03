# RunbookPilot design plan (Phase 1)

Date: 2026-11-03. Branch `ui-redesign`. Input: `UI_REDESIGN_PLAN.md` sections 3 to 8, `docs/ui-audit.md`, `docs/audit/*.png`.
Status: draft. Waits for the owner's OK before Phase 2.

**Direction in one line:** keep the calm hairline Geist look the audit liked, move it to a cool slate base, take the red-orange accent away from branding, and spend all the visual weight on one thing: the command block with its risk tab.

Why keep the look: the audit lists "hairline, dense, calm, Geist, no gradients" as what works, and it fits plan section 4 ("like a good ticketing tool or a code review tool"). The problems are order, words, labels, scale and mobile, not the style. A new style costs Phase 2 time and gives no gain for the judges.

---

## 1. Principles

1. **Workbench first.** The first screen is the triage tool in a working state, with a "Run demo" button. No hero, no tour. (Plan 3, 8)
2. **Answer before admin.** The result reads verdict, cause, steps, commands. Request IDs, model, scores go to collapsed Details. (Plan 6)
3. **Color means risk, nothing else.** Teal = read-only, amber = needs approval, red = escalate. One cobalt accent for primary actions. Priority, confidence and status use neutral ink. (Plan 4)
4. **Text before color.** Every risk mark has a word and an icon. Color is a second signal only. (Plan 7)
5. **One bold thing.** The command block is loud. Everything else is quiet: hairlines, no shadows, no cards in cards. (Plan 4)
6. **Never pretend.** Sample and staged data says so where it shows. Commands say "not run" where they show. (Plan 2.2, 2.4)
7. **Plain words.** Sentence case, active voice, a button says what it does. Raw terms only in Details. (Plan 6a)

---

## 2. Color tokens

Cool slate neutrals. CSS names are the Phase 2 token names in `static/css/tokens.css`.

### Neutrals and brand

| Token | Use | Light | Dark |
|---|---|---|---|
| `--bg` | page | `#f5f6f8` | `#0e1014` |
| `--surface` | panels, inputs | `#ffffff` | `#14171c` |
| `--surface-2` | hover, selected row, zebra | `#eef0f3` | `#1b1f25` |
| `--line` | hairlines (decorative) | `#dde1e7` | `#272c34` |
| `--line-strong` | input and control borders | `#7c8592` | `#69727f` |
| `--text` | primary text | `#12161c` | `#e7e9ed` |
| `--text-2` | secondary text | `#4b5563` | `#a9b0bb` |
| `--text-3` | meta, captions (min) | `#5c6573` | `#8f98a5` |
| `--accent` | primary button fill, focus ring, links | `#2b4acb` | `#3d5ae0` (fill) / `#9aabff` (text, focus) |
| `--ink` | command block surface (both themes) | `#10141a` | `#07090c` |
| `--ink-text` / `--ink-muted` | command text / `PS>` prompt | `#e6e9ee` / `#9aa3b0` | same |

### Risk colors (meaning only)

| Meaning | Token set | Light fg / bg / tab | Dark fg / bg / tab |
|---|---|---|---|
| Read-only (teal) | `--ro`, `--ro-bg`, `--ro-on` | `#0b6b5d` / `#e3f4f0` / tab `#0b6b5d` + white | `#5fd3bd` / `#0f2723` / tab `#5fd3bd` + `#04201b` |
| Needs approval (amber) | `--na`, `--na-bg`, `--na-solid`, `--na-on` | `#8a4b00` / `#fdf1dc` / tab `#f2b530` + `#2a1a00` | `#f3c262` / `#2a2010` / tab `#f3c262` + `#2a1a00` |
| Escalate (red) | `--esc`, `--esc-bg`, `--esc-on` | `#b42318` / `#fdecea` / tab `#b42318` + white | `#ff8e84` / `#2d1513` / tab `#ff8e84` + `#2d0a07` |

**Confidence (neutral scale):** a 3-segment meter plus a word. High = 3 filled, Medium = 2, Low = 1. Filled = `--text-2`, empty = `--line-strong`. Never red or green.
**Queue priority:** neutral text badge ("Critical", "High", "Medium"); Critical gets weight 600, not red. Red is kept for escalation.

### Contrast (WCAG 2.x, computed with a script; AA text = 4.5, UI parts = 3.0)

| Pair | Light | Dark |
|---|---|---|
| `--text` on `--bg` / `--surface` | 16.8 / 18.2 | 15.7 / 14.8 |
| `--text-2` on `--bg` / `--surface` / `--surface-2` | 7.0 / 7.6 / 6.6 | 8.7 / 8.2 / 7.6 |
| `--text-3` on `--bg` / `--surface` / `--surface-2` | 5.5 / 5.9 / 5.2 | 6.5 / 6.2 / 5.7 |
| White on `--accent` (primary button) | 7.1 | 5.6 |
| Accent text on `--surface` (links, focus) | 7.1 | 8.3 (`#9aabff`) |
| `--ink-text` / `--ink-muted` on `--ink` | 15.2 / 7.3 | 16.4 / 7.8 |
| `--ro` on `--ro-bg` / on `--surface` / tab text | 5.6 / 6.4 / 6.4 | 8.6 / 9.9 / 9.4 |
| `--na` on `--na-bg` / on `--surface` / tab text | 6.1 / 6.8 / 9.2 | 9.7 / 10.9 / 10.2 |
| `--esc` on `--esc-bg` / on `--surface` / tab text | 5.8 / 6.6 / 6.6 | 7.7 / 8.1 / 8.2 |
| `--line-strong` on `--surface` / `--bg` (UI 3:1) | 3.7 / 3.5 | 3.7 / 3.9 |
| Dark `--accent` fill on `--surface` (button edge) | — | 3.2 |

One known non-text gap: the light amber tab fill `#f2b530` on white is 1.8:1. Fix: the tab gets a 1 px `--na` border, and the block's 4 px left rail uses `--na` (6.8:1). The word "Needs approval" carries the meaning anyway.

---

## 3. Type

- **UI sans:** Geist (variable, 400 to 600). **Mono:** Geist Mono (400, 500). Mono only for commands, event IDs, hex codes, ticket IDs, host names and request IDs. Not for labels, chips, counters or scores.
- **Loading:** self-host `static/fonts/Geist-Variable.woff2` and `GeistMono-Variable.woff2` (OFL licence, from the `geist` npm package files) with `@font-face { font-display: swap; }` and one `<link rel="preload">` for the sans. Fallback stacks: `"Geist", "Segoe UI", system-ui, sans-serif` and `"Geist Mono", "Cascadia Mono", Consolas, monospace`. If vendoring fails, keep the Google Fonts link (it already uses `display=swap`).
- **Numbers:** `font-variant-numeric: tabular-nums` on timers, counts, confidence.
- **Measure:** prose blocks `max-width: 72ch`.

| Token | Size / line | Weight | Use |
|---|---|---|---|
| `--fs-xs` | 13 / 18 | 500 | badges, captions, meta (the floor; nothing smaller) |
| `--fs-sm` | 14 / 20 | 400, 500 | labels, buttons, rail, queue meta |
| `--fs-base` | 15 / 24 | 400 | body, steps, ticket text |
| `--fs-md` | 17 / 26 | 600 | section headings in a view |
| `--fs-lg` | 20 / 28 | 600 | view title, diagnosis sentence |
| `--fs-xl` | 24 / 32 | 600 | verdict state word |
| `--fs-code` | 14 / 22 mono | 400 (500 for `PS>`) | command block |
| `--fs-code-sm` | 13 / 20 mono | 400 | IDs, hosts inside text |

Seven sizes replace the 24 sizes the audit counted. Ratio is about 1.125.

---

## 4. Spacing, radius, borders, targets

- **Spacing (4 px base):** `--sp-1` 4, `--sp-2` 8, `--sp-3` 12, `--sp-4` 16, `--sp-5` 24, `--sp-6` 32, `--sp-7` 48. Inside a panel: 16. Between sections of the result: 24. View gutter: 24 desktop, 16 at 390 px.
- **Radius:** 6 px controls and inputs, 8 px panels and command blocks, 4 px badges and tabs. No pill shapes except the confidence meter segments (2 px).
- **Borders:** 1 px `--line` between sections (hairline rhythm, no card per section). 1 px `--line-strong` around inputs, selects, secondary buttons. Risk blocks get a 4 px left rail in the risk color.
- **Shadows:** none, except the toast (`0 4px 16px rgb(0 0 0 / .16)`) and the mobile menu sheet.
- **Focus:** `outline: 2px solid var(--accent-text-or-fill); outline-offset: 2px` on `:focus-visible` everywhere. Never removed.
- **Touch targets:** buttons, inputs, selects, rail items, queue rows, step checkboxes (whole row is the label) at least 40 px high. Icon-only buttons are 40 × 40. Rail items 44 px.
- **Motion:** 120 ms for hover and press, 180 ms ease-out for expand and for the one "result arrived" fade (opacity 0 to 1, 4 px rise on the verdict strip only). Under `prefers-reduced-motion: reduce`, all durations become 0.

---

## 5. Layout wireframes

### Breakpoints

| Width | Rail | Main |
|---|---|---|
| ≥ 1200 | 216 px, icon + label | two columns: left `minmax(360px, 420px)`, right `1fr` |
| 960 to 1199 | 64 px, icon only (`aria-label` + visible tooltip on hover/focus) | two columns: left 380 px, right `1fr` |
| 768 to 959 | 64 px icon rail | one column: input, then result |
| < 768 (390) | no rail; "Menu" button in top bar opens the nav as a sheet under the bar | one column |

### Top bar (plan section 5)

```
Desktop (≥ 960), 56 px high, sticky
┌────────────────────────────────────────────────────────────────────────────┐
│ ▣ RunbookPilot          Model: Muse Spark 1.3   ● 18 runbooks loaded   [☾] │
└────────────────────────────────────────────────────────────────────────────┘
  index status: ● loaded (neutral dot + text) │ ◌ Loading runbooks… │ ▲ Runbooks failed to load. Retry

390 px, 56 px high
┌──────────────────────────────────────┐
│ [≡ Menu]  RunbookPilot  · Triage  ● [☾]│   ● = index status dot with sr-only text
└──────────────────────────────────────┘
  Model badge moves into the menu sheet footer. Theme button is 40 × 40, icon + aria-label
  "Switch to dark theme" (says the action; fixes the audit's toggle confusion).
```

### Desktop triage (1440)

```
┌───────────┬──────────────────────────────────────────────────────────────────────────┐
│ TOP BAR (full width)                                                                  │
├───────────┼──────────────────────────────┬───────────────────────────────────────────┤
│ ▸ Triage  │ Ticket                        │  RESULT (see order below)                │
│   Runbooks│ ┌──────────────────────────┐  │                                           │
│   Safety  │ │ ticket text (12 rows)    │  │                                           │
│     lab   │ │                          │  │                                           │
│   Bench-  │ └──────────────────────────┘  │                                           │
│     mark  │ 0 / 4000      [Clear] [Analyze ticket]                                   │
│   Integr- │ Mode ( Standard | Deep )                                                  │
│   ations  │  Deep: the model reasons longer. Slower, about 10 s.                      │
│           │ [ + Attach screenshot ] drop zone, 64 px                                  │
│           │ ─────────────────────────────                                             │
│           │ Samples                                                                   │
│           │  AD lockout · Event 4740 locks a user every 15 min                        │
│           │  VSS backup stall · Nightly image backup times out                        │
│           │  M365 mail queue · Outbound mail delayed                                   │
│           │  Uncovered VoIP · No runbook covers this (escalates)                       │
│           │  RDP dialog screenshot · Image only                                        │
│           │ ─────────────────────────────                                             │
│           │ Queue   [Sample data]   6        [Refresh]                                │
│           │  ConnectWise PSA · 2 h · High                                             │
│           │  Recurring AD account lockout for user01                                  │
│           │  … all 6 rows, no nested scroll                                           │
└───────────┴──────────────────────────────┴───────────────────────────────────────────┘
```
Ticket box sits above samples and queue so the first action is obvious. Samples and queue are lists (40 px+ rows), not chips. Selecting a queue row or sample fills the box and scrolls the box into view on mobile.

### Result area (plan section 6 order)

```
┌ VERDICT STRIP ───────────────────────────────────────────────────────────────┐
│ ▌ Needs approval steps          ▮▮▯ Medium confidence   2 runbooks matched    │
│   2 read-only, 2 change the system                                            │
└──────────────────────────────────────────────────────────────────────────────┘
  (left rail + state word in the risk color: teal "Covered by runbooks",
   amber "Needs approval steps", red "Escalate to Tier 3")

Likely cause                                                                   
A stale saved password (Credential Manager, a disconnected RDP session or a   
phone mail app) keeps locking user01 after the password change.               

Steps                                                         1 of 4 done
 [x] 1  Check if the account is locked and read bad-password counters
 [ ] 2  Find the caller machine in Event 4740 on the domain controller
 [ ] 3  Unlock the account after you verify the user
 [ ] 4  Clear cached credentials on the source machine
      (ticks stay in this browser only)

Commands                       RunbookPilot never runs commands. Copy and run them yourself.
 ── Read-only (2) ──
 [COMMAND BLOCK, teal]  (section 6)
 [COMMAND BLOCK, teal]
 ┌ ▲ Changes the system. Needs approval. ──────────────────────────────┐
 │ Check the scope and get approval before you run these 2 commands.   │
 └──────────────────────────────────────────────────────────────────────┘
 [COMMAND BLOCK, amber]
 [COMMAND BLOCK, amber]

Source runbooks
 ▸ Locked Active Directory user account                         rb-02
 ▸ Active Directory forgotten or expired password               rb-16
   (expand: source runbook text, read-only, max-height 320 px, own scroll)

[ESCALATION PANEL — only when escalate = true, red left rail]
 Escalate to Tier 3
 No runbook covers a VoIP handset TFTP boot loop. (reason text from API)
 [Draft a runbook]  [Flag for Tier 3]

▸ Details  (collapsed)
   Request ID · Model · Mode · Time 9.9 s · Retrieval scores (BM25L) ·
   Safety overrides · RMM device telemetry [Sample data] · Re-run with RMM output

┌ WRITEBACK BAR (sticky to bottom of the result column on desktop) ───────────┐
│ Send to  [ConnectWise PSA ▾]   [Post internal note]  [Flag for Tier 3]       │
│ Staged, not sent to a live PSA.                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Empty state (result column, first load)

```
┌──────────────────────────────────────────────────────────────┐
│ Paste a ticket, pick a sample, or run the demo.               │
│ RunbookPilot matches the ticket to 18 runbooks and gives a    │
│ fix plan with safe, labelled PowerShell commands.             │
│                                                               │
│ [ Run demo ]   Loads the AD lockout sample and analyzes it.   │
│                                                               │
│ What you get                                                  │
│  ▌ Read-only     safe to run, only reads state                │
│  ▌ Needs approval changes the system                          │
│  ▌ Escalate      no runbook covers it                         │
└──────────────────────────────────────────────────────────────┘
After a result: one quiet line under the verdict strip —
"Next: try the Uncovered VoIP sample, or test a command in the Safety lab."
```
The 18-row runbook list leaves the empty state and moves to `#runbooks`.

### Loading and error (result column)

```
Loading: skeleton of verdict strip + 2 text lines + 4 step rows + 2 command blocks
         "Analyzing ticket… 4.2 s"  (aria-live polite, no fake stage names)
Error:   ┌ ▲ The model is busy. Wait 28 s, then try again. ─── [Try again] ┐
         │ Your ticket text is kept.                                     │
         └───────────────────────────────────────────────────────────────┘
         Try again is disabled with a countdown while Retry-After runs.
```

### Mobile 390 px

```
┌──────────────────────────────────────┐
│ [≡ Menu] RunbookPilot · Triage ● [☾] │  sticky 56 px
├──────────────────────────────────────┤
│ (Menu open: sheet under the bar,     │
│  5 rows × 48 px, current marked,     │
│  model badge at the bottom. Esc and  │
│  outside tap close it.)              │
├──────────────────────────────────────┤
│ Ticket box (8 rows)                  │
│ 0 / 4000          [Analyze ticket]   │  full-width button below box
│ Mode ( Standard | Deep )             │
│ [+ Attach screenshot]                │
│ ▸ Samples (5)          collapsed     │  <details>, open on empty state
│ ▸ Queue · Sample data (6)            │  <details>
├──────────────────────────────────────┤
│ Result (same order as desktop)       │
│ Command blocks: code wraps           │
│ (white-space: pre-wrap), no page     │
│ scroll sideways                      │
│ Writeback bar: not sticky, at end    │
└──────────────────────────────────────┘
```
Every row stacks; no fixed widths over 358 px. Long IDs and hosts use `overflow-wrap: anywhere`.

---

## 6. The bold element: command block

```
 ┌──────────────────┐
 │ 👁 Read-only      │ Check lockout state and bad-password counters   [⧉ Copy]
 ├──────────────────┴──────────────────────────────────────────────────────────┐
 ┃ PS> Get-ADUser -Identity user01 -Properties LockedOut, AccountLockoutTime, │
 ┃     BadPwdCount, LastBadPasswordAttempt                                    │
 ├────────────────────────────────────────────────────────────────────────────┤
 ┃ Not run by RunbookPilot.                              [Stage RMM check]     │
 └────────────────────────────────────────────────────────────────────────────┘
 ┃ = 4 px risk rail, full height
```

- **Risk tab:** a solid tab sitting on the top-left edge of the block, 28 px high, radius 4 4 0 0, risk fill + on-color text, icon + word at `--fs-xs` 600. Read-only = eye icon, "Read-only". Needs approval = hand/stop icon, "Needs approval". The word is always there (not color only); `aria-label` on the block: "Read-only command" / "Command that changes the system. Needs approval."
- **Purpose line:** the step text, `--fs-sm`, `--text`, one line, wraps.
- **Code:** `--ink` surface in both themes, `--fs-code`, `PS>` prompt in `--ink-muted` 500 and `user-select: none`, command `--ink-text`, `white-space: pre-wrap; overflow-wrap: anywhere`, padding 16. The 4 px left rail in the risk color runs the full block height.
- **Footer:** "Not run by RunbookPilot." in `--text-3` at `--fs-xs` in every block (plan rule 2.2), plus the staged RMM action button (secondary).
- **States:**
  - Default: 1 px `--line` border, rail in risk color.
  - Hover / focus-within: border turns the risk color (`--ro`/`--na`), Copy button gets `--surface-2` fill. 120 ms. No lift, no shadow.
  - Copied: Copy button text becomes "Copied" with a check icon for 2 s, an `aria-live="polite"` region says "Command copied", the rail pulses once to 8 px (180 ms; no pulse under reduced motion). Clipboard failure: button says "Select and copy" and the command text gets selected.
- **Groups:** read-only group first, header "Read-only (2)". Then the needs-approval group with an amber warning panel above it: "▲ Changes the system. Needs approval." + "Check the scope and get approval before you run these N commands." (`role="note"`). Escalate tickets have no commands; the escalation panel replaces the group.
- **Section note:** above the groups, once: "RunbookPilot never runs commands. Copy and run them yourself."

---

## 7. Components and file split for Phase 2

### Components (`static/css/components.css`)

| Component | Variants / notes |
|---|---|
| Button | primary (accent fill, one per view area), secondary (outline `--line-strong`), quiet (text only), icon (40 × 40, `aria-label`). Min height 40. `disabled` + `aria-busy`. No arrows. |
| Badge | neutral, risk (ro / na / esc), staged ("Sample data", "Staged, not live": dashed `--line-strong` border, `--text-2`). Always text. |
| Risk tab | the solid command tab (section 6). |
| Input / textarea / select | 40 px min, `--line-strong` border, label above, help text below, counter. |
| Segmented control | Standard / Deep, radio inputs styled as segments. |
| Drop zone | file input + label, preview thumbnail, Remove button. |
| Panel / section | hairline-separated block with heading; no shadow. |
| Notice | info / warning (amber) / danger (red) / staged; left rail + icon + text; optional action. |
| Verdict strip | state word, confidence meter, counts. |
| Confidence meter | 3 segments + word. |
| Checklist | `<ol>` of `<label><input type=checkbox>` rows; ticks in `localStorage` keyed by request ID, wrapped in try/catch. |
| Disclosure | `<details>/<summary>` styled; used for runbooks, Details, mobile Samples/Queue. |
| List row | queue item, sample item, runbook item; whole row is a button, 44 px+. |
| Command block | section 6. |
| Toast | bottom-right (bottom full-width at 390), `role="status"`, 4 s, same word as the button ("Note posted (staged)"). |
| Skeleton | shimmer only when motion allowed; static blocks otherwise. |
| Rail / nav item | icon + label, `aria-current="page"`. |
| Table | benchmark scorecard; stacks to rows at 390. |

### Files

```
static/
  index.html            shell: top bar, rail, 5 <section data-view> blocks, <template>s
  fonts/                Geist-Variable.woff2, GeistMono-Variable.woff2
  css/tokens.css        @font-face, color tokens light/dark, type, space, radius, motion
  css/base.css          reset, body, type roles, focus, skip link, reduced motion, .sr-only
  css/layout.css        shell grid, top bar, rail, menu sheet, columns, breakpoints
  css/components.css    the table above
  css/views.css         triage, result, command block, runbooks, safety, benchmark, integrations
  js/main.js            boot: theme, router, index status, view init
  js/router.js          hash routes, #eval → #benchmark alias, focus view heading on change
  js/dom.js             el(tag, props, ...children) — sets textContent only; clear(node)
  js/api.js             fetch wrapper; maps 429 (Retry-After header), 504, 502, 500, 503, 422, network
  js/copy.js            raw term → UI text map (section 8)
  js/theme.js           system default, toggle, localStorage
  js/toast.js           toast queue
  js/store.js           safe localStorage get/set (step ticks, theme, last route)
  js/views/triage.js    input, samples, queue, screenshot, mode, submit, states
  js/views/result.js    verdict, steps, commands, runbooks, escalation, details, writeback
  js/views/runbooks.js  list + search + reader
  js/views/safety.js    sandbox
  js/views/benchmark.js scorecard
  js/views/integrations.js connectors (staged)
```
Load with `<script type="module" src="/static/js/main.js">`. CSS as 5 `<link>` tags in order. Checked: Python maps `.js` to `application/javascript` and `.woff2` to `font/woff2` on this machine, and Vercel `includeFiles` already covers `static/**`.

### Hash routes (plan section 5)

| Route | View | Rail label |
|---|---|---|
| `#triage` (default, also empty hash) | Triage | Triage |
| `#runbooks` | Runbooks | Runbooks |
| `#safety` | Safety lab | Safety lab |
| `#benchmark` (`#eval` redirects here) | Benchmark | Benchmark |
| `#integrations` | Integrations, "Staged, not live" banner | Integrations |

Route change: show one `<section>`, set `aria-current`, update `document.title` ("Triage · RunbookPilot"), move focus to the view `<h1>`.

---

## 8. Copy rules and term map

Rules: sentence case; active voice; no all-caps labels; a button names its action; the toast repeats the button word; raw terms only inside Details; numbers with units ("9.9 s"); no filler or marketing words.

| Raw term / old text | UI text |
|---|---|
| `read_only` | Read-only |
| `needs_approval` | Changes the system. Needs approval. (tab: "Needs approval") |
| `escalate: true` | Escalate to Tier 3 |
| `executed_on_host: false` | Not run. RunbookPilot never runs commands. |
| `2 read_only, 2 needs_approval` | 2 read-only, 2 change the system |
| high / medium / low confidence | High / Medium / Low confidence |
| Remediation sequence | Steps |
| PowerShell commands & RMM dispatch | Commands |
| Matched runbooks: … (BM25 172.5) | Source runbooks (score only in Details as "BM25L score") |
| Queue RMM check / Request RMM change | Stage RMM check / Stage RMM change request |
| Hot-index runbook & re-analyze ticket | Add this runbook and re-run triage |
| Draft new runbook with Muse Spark | Draft a runbook |
| Flag for Tier 3 escalation | Flag for Tier 3 |
| `muse-spark-1.3 / standard` | Details: Model Muse Spark 1.3 · Mode Standard |
| Safety audit: verified | Details: Safety rules checked every command |
| Meta mode: Standard reasoning / Deep reasoning (multi-hop) | Mode: Standard / Deep, "Deep: the model reasons longer. Slower." |
| Pending PSA & RMM queue · 6 items | Queue · Sample data · 6 |
| critical / high / medium | Critical / High / Medium |
| 18 runbooks indexed / Index loading… | 18 runbooks loaded / Loading runbooks… |
| Display-only, Integrations 0/12, Safety & Eval 100% | removed from the top bar |
| No ticket loaded | Paste a ticket, pick a sample, or run the demo. |
| unconfigured | Not set up |
| Standby mode (connectors staged, live polling inactive) | Staged, not live. Nothing is sent or received. |
| Deterministic classifier verdict | Safety rule result |
| TOP-3 HIT / ESCALATE | Found in top 3 / Escalated, as expected |
| BM25 top-3 hit rate | Right runbook in the top 3 |
| Unsafe labeled read_only: 0 mislabeled | Commands that change the system but marked read-only: 0 |
| 429 Rate limit exceeded | The model is busy. Wait N s, then try again. |
| 504 timeout | The model took too long. Try again, or use Standard mode. |
| 502 `upstream` / 500 | The model sent no usable answer. Try again. |
| 503 | The service is not ready. Wait a moment, then try again. |
| 422 Extra inputs… | The ticket could not be read. Check the text and try again. |
| network failure | No connection to RunbookPilot. Check the server, then try again. |

Error panels show the raw `detail` and request ID inside a collapsed "Technical details" only.

---

## 9. Audit top 10: how each is solved

1. **390 px top bar breaks, page scrolls sideways** → rail becomes a Menu sheet, top bar has 4 items max, one-column stack, `pre-wrap` commands, `overflow-wrap: anywhere`; Phase 6 checks `scrollWidth ≤ 390`.
2. **Wrong result order, no verdict strip** → fixed section 6 order with the verdict strip first; IDs and model go to Details; writeback bar moves to the end.
3. **Raw API terms** → `js/copy.js` term map (section 8); raw terms only in Details.
4. **Sample/staged data not labelled** → "Sample data" badge on queue and telemetry, "Staged, not sent to a live PSA" on writeback, "Staged, not live" on Integrations.
5. **Empty state is a spec sheet** → invitation text, "Run demo" primary button, 3-line risk legend; runbook list moves to `#runbooks`.
6. **Nav wrong, no Runbooks view** → left rail with 5 hash routes; Safety lab and Benchmark split; count chips removed.
7. **Input column crowded** → ticket box first, one primary button, samples as a described list, Mode as a segmented control with a help line, queue as a full list without nested scroll.
8. **Weak error/loading states** → error panel with cause, next step, "Try again", Retry-After countdown; skeleton shaped like the result with elapsed timer.
9. **Tiny type, 24 sizes, small targets, contrast fails** → 7-size scale with a 13 px floor, mono for code only, 40 px targets, every pair above checked AA.
10. **Command block weak, no tickable steps, runbooks do not expand** → bold command block (section 6) with never-run note in each block, checklist steps, `<details>` source runbooks with the runbook text.

---

## 10. Review against plan section 4

| Section 4 item | Check |
|---|---|
| Mood: calm, precise, dense | Pass. Hairlines, 15 px body, no hero. |
| Layout: left rail + two columns, single on mobile | Pass. Rail collapses to icons, then to a Menu sheet. |
| Cool neutral base | Pass. Slate `#f5f6f8` / `#0e1014`, not zinc gray. |
| Color only for meaning; confidence neutral; one accent | Pass after the change below. Priority badges also lost their red/amber. |
| Avoid: cream + terracotta | Pass. No warm base. |
| Avoid: near-black + acid green | Pass. Old dark read-only green `#7ee787` becomes teal `#5fd3bd`; base gets a blue-slate tint. |
| Avoid: identical rounded cards with soft shadow | Pass. Sections use hairlines; only the command block, verdict strip and notices have a frame, each a different shape. No shadows. |
| Avoid: all-caps tracked labels | Pass. "TOP-3 HIT"/"ESCALATE" go away; sentence case everywhere. |
| Avoid: arrows on every button | Pass. No arrow glyphs on buttons. |
| Avoid: gradient decoration | Pass. None. |
| Type: one sans, one mono for code/IDs/hex only, real scale, < 80 ch | Pass. Geist + Geist Mono, 7 sizes, 72 ch. |
| Theme: light + dark, system default, toggle stays | Pass. Contrast table covers both. |
| Motion only on user action + one result change, reduced motion | Pass. Section 4 motion rules. |
| Bold in one place | Pass. Command block only. |

**The one change after review: the brand accent moved from red-orange (`#e54d2e`) to cobalt (`#2b4acb` / `#3d5ae0`).**
My first draft kept the current red-orange logo square and focus ring because the audit liked the look. The review against "colors carry meaning, use them only for meaning" showed the problem: red-orange sits next to escalate red. A judge sees a red-orange focus ring or logo and reads "danger". The audit screenshot `focus-1440.png` shows the red-orange 2 px ring on a plain tab. Cobalt has no risk meaning here, keeps 7.1:1 for white text, and leaves red only for "Escalate to Tier 3".

Other things to flag (not changed, for the owner):
- Plan section 6 says "Run a sample ticket", section 8 says "Run demo". I use one button, "Run demo", with a line that says it runs a sample ticket.
- The LLM pairs "Clear cached credentials" with `Clear-RecycleBin -Confirm` (audit backend note 1). The bold command block will make this wrong command more visible in the demo. Fix is in the prompt or runbook, out of UI scope.
