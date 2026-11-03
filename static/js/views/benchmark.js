// Benchmark: retrieval and safety scorecard from /eval/summary.

import { el, byId, clear, setText, show, badge, notice } from "../dom.js";
import { get } from "../api.js";

let ui = {};
let loaded = false;

function resultBadge(row) {
  if (row.expected_escalate && !row.expected_runbook_id) return badge("Escalated, as expected");
  if (row.retrieval_hit) return badge("Found in top 3", "strong");
  return badge("Missed", "esc");
}

function topMatches(row) {
  const top = Array.isArray(row.top_matches) ? row.top_matches : [];
  if (!top.length) return el("span", { class: "text-3", text: "None" });
  return el(
    "ol",
    { class: "bench-top" },
    ...top.map((m) =>
      el("li", { class: m.id === row.expected_runbook_id ? "bench-top-hit" : null }, el("span", { class: "mono wrap-anywhere", text: m.id }), el("span", { class: "tabular text-3", text: " " + Number(m.score).toFixed(1) }))
    )
  );
}

function expectedCell(row) {
  if (!row.expected_runbook_id) return el("span", { text: "None. It should escalate." });
  const match = (row.top_matches || []).find((m) => m.id === row.expected_runbook_id);
  return el(
    "span",
    { class: "stack bench-expected" },
    match ? el("span", { text: match.title }) : null,
    el("span", { class: "mono t-xs text-3 wrap-anywhere", text: row.expected_runbook_id })
  );
}

function showError(message) {
  clear(ui.status).appendChild(
    notice(
      "danger",
      "The benchmark did not load.",
      message,
      el("div", { class: "btn-row notice-actions" }, el("button", { type: "button", class: "btn btn-secondary", text: "Try again", on: { click: load } }))
    )
  );
  ["hit", "split", "cmds", "unsafe"].forEach((k) => setText(ui[k], "—"));
  show(ui.unsafeState, false);
  clear(ui.rows);
}

async function load() {
  ui.refresh.disabled = true;
  ui.refresh.setAttribute("aria-busy", "true");
  clear(ui.status).appendChild(el("p", { class: "t-sm text-2", text: "Running the test…" }));
  const res = await get("/eval/summary");
  ui.refresh.disabled = false;
  ui.refresh.removeAttribute("aria-busy");
  if (!res.ok || !res.data) {
    showError(res.message || "Try again.");
    return;
  }
  loaded = true;
  clear(ui.status);
  const d = res.data;
  const rate = Number(d.bm25_top3_hit_rate || 0).toFixed(1) + "%";
  setText(ui.hit, d.bm25_top3_hits + " of " + d.covered_tickets + " (" + rate + ")");
  setText(ui.split, d.total_tickets + " tickets: " + d.covered_tickets + " with a runbook, " + d.escalation_tickets + " that should escalate");
  setText(ui.cmds, d.commands_audited + " commands in " + d.runbooks_audited + " runbooks");
  setText(ui.unsafe, String(d.mislabeled_needs_approval));
  const clean = Number(d.mislabeled_needs_approval) === 0;
  ui.unsafeState.className = "badge " + (clean ? "badge-strong" : "badge-esc");
  setText(ui.unsafeState, clean ? "Pass" : "Needs a fix");
  show(ui.unsafeState, true);

  clear(ui.rows);
  (d.rows || []).forEach((row) => {
    ui.rows.appendChild(
      el(
        "tr",
        null,
        el("td", { class: "mono", "data-label": "Ticket", text: row.ticket_id }),
        el("td", { "data-label": "Expected runbook" }, expectedCell(row)),
        el("td", { "data-label": "Top 3 matches (search score)" }, topMatches(row)),
        el("td", { "data-label": "Result" }, resultBadge(row))
      )
    );
  });
}

export function initBenchmark() {
  ui = {
    refresh: byId("btn-refresh-eval"),
    status: byId("bench-status"),
    hit: byId("eval-metric-hitrate"),
    split: byId("eval-metric-split"),
    cmds: byId("eval-metric-commands"),
    unsafe: byId("eval-metric-unsafe"),
    unsafeState: byId("eval-metric-unsafe-state"),
    rows: byId("eval-rows")
  };
  ui.refresh.addEventListener("click", load);
}

export function onBenchmarkShown() {
  if (!loaded) load();
}
