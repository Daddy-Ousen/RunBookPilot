// Benchmark: retrieval and safety scorecard from /eval/summary.

import { el, byId, clear, setText, badge } from "../dom.js";
import { get } from "../api.js";

let ui = {};
let loaded = false;

function verdict(row) {
  if (row.expected_escalate && !row.expected_runbook_id) return badge("Escalated, as expected");
  if (row.retrieval_hit) return badge("Found in top 3", "ro");
  return badge("Missed", "esc");
}

async function load() {
  ui.refresh.disabled = true;
  const res = await get("/eval/summary");
  ui.refresh.disabled = false;
  if (!res.ok || !res.data) {
    clear(ui.rows).appendChild(el("tr", null, el("td", { colspan: "4", text: res.message || "The benchmark did not load." })));
    return;
  }
  loaded = true;
  const d = res.data;
  const rate = Number(d.bm25_top3_hit_rate || 0).toFixed(1) + "%";
  setText(ui.hit, d.bm25_top3_hits + " of " + d.covered_tickets + " (" + rate + ")");
  setText(ui.split, d.covered_tickets + " covered, " + d.escalation_tickets + " should escalate");
  setText(ui.cmds, d.commands_audited + " commands in " + d.runbooks_audited + " runbooks");
  setText(ui.unsafe, String(d.mislabeled_needs_approval));

  clear(ui.rows);
  (d.rows || []).forEach((row) => {
    const top = (row.top_matches || []).map((m) => m.id + " (" + m.score + ")").join(", ") || "None";
    ui.rows.appendChild(
      el(
        "tr",
        null,
        el("td", { class: "mono", "data-label": "Ticket", text: row.ticket_id }),
        el("td", { class: "mono wrap-anywhere", "data-label": "Expected runbook", text: row.expected_runbook_id || "None (should escalate)" }),
        el("td", { class: "mono wrap-anywhere text-2", "data-label": "Top 3 matches", text: top }),
        el("td", { "data-label": "Result" }, verdict(row))
      )
    );
  });
}

export function initBenchmark() {
  ui = {
    refresh: byId("btn-refresh-eval"),
    hit: byId("eval-metric-hitrate"),
    split: byId("eval-metric-split"),
    cmds: byId("eval-metric-commands"),
    unsafe: byId("eval-metric-unsafe"),
    rows: byId("eval-rows")
  };
  ui.refresh.addEventListener("click", load);
}

export function onBenchmarkShown() {
  if (!loaded) load();
}
