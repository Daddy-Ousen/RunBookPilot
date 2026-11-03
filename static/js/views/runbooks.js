// Runbook index: top bar status, the runbooks list and search.

import { el, byId, clear, setText, show } from "../dom.js";
import { get } from "../api.js";
import { state, on } from "../store.js";

let ui = {};
let items = [];
let loading = null;

function setStatus(kind, text) {
  ui.status.dataset.state = kind;
  setText(ui.statusText, text);
  show(ui.retry, kind === "error");
}

function renderList() {
  const q = ui.search.value.trim().toLowerCase();
  const shown = items.filter((rb) => !q || (rb.title + " " + rb.id).toLowerCase().includes(q));
  clear(ui.list);
  setText(ui.count, shown.length === items.length ? items.length + " runbooks" : shown.length + " of " + items.length + " runbooks");
  if (!shown.length) {
    ui.list.appendChild(el("li", { class: "list-empty", text: items.length ? "No runbook matches your search." : "No runbooks loaded." }));
    return;
  }
  shown.forEach((rb) => {
    ui.list.appendChild(
      el(
        "li",
        { class: "list-row list-row-static" },
        el("span", { class: "list-row-top" }, el("span", { class: "list-row-title", text: rb.title }), el("span", { class: "mono text-3", text: rb.id }))
      )
    );
  });
}

export async function loadIndex() {
  setStatus("loading", "Loading runbooks…");
  const [health, list] = await Promise.all([get("/health"), get("/runbooks")]);
  if (!health.ok || !list.ok || !Array.isArray(list.data)) {
    setStatus("error", "Runbooks failed to load.");
    return false;
  }
  items = list.data.filter((rb) => rb && typeof rb.id === "string" && typeof rb.title === "string");
  state.runbookTitles.clear();
  items.forEach((rb) => state.runbookTitles.set(rb.id, rb.title));
  const n = health.data.runbooks_loaded || items.length;
  setStatus("loaded", n + " runbooks loaded");
  setText(byId("empty-runbook-count"), String(n));
  renderList();
  return true;
}

// Loads the index once if it is not loaded yet.
export function ensureIndex() {
  if (state.runbookTitles.size > 0) return Promise.resolve(true);
  if (!loading) loading = loadIndex().finally(() => (loading = null));
  return loading;
}

export function initRunbooks() {
  ui = {
    status: byId("index-status"),
    statusText: byId("index-status-text"),
    retry: byId("index-retry-btn"),
    list: byId("runbook-list"),
    search: byId("runbook-search"),
    count: byId("runbook-count")
  };
  ui.retry.addEventListener("click", () => loadIndex());
  ui.search.addEventListener("input", renderList);
  on("index-changed", () => loadIndex());
  loadIndex();
}
