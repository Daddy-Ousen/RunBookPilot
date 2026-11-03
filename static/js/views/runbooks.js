// Runbooks: top bar index status, the runbook list with search, and the reader.
// Source text comes from the static copies in /static/runbooks/ (see runbook-text.js).

import { el, byId, clear, setText, show } from "../dom.js";
import { get } from "../api.js";
import { state, on } from "../store.js";
import { runbookText, isSessionRunbook, failedMessage } from "../runbook-text.js";
import { parseFrontMatter, renderMarkdown, shortLine } from "../markdown.js";

let ui = {};
let items = []; // [{ id, title }]
let loading = null;
let selectedId = null;
const info = new Map(); // id -> { tags, short, haystack } once its text is read, or { missing: true }
let prefetching = false;
let viewShown = false; // the text of all runbooks loads only after this view was opened

const wide = () => window.matchMedia("(min-width: 960px)").matches;

function setStatus(kind, text) {
  ui.status.dataset.state = kind;
  setText(ui.statusText, text);
  show(ui.retry, kind === "error");
}

function badgeFor(id) {
  if (isSessionRunbook(id)) return el("span", { class: "badge badge-staged", text: "Added in this session" });
  const i = info.get(id);
  if (i && i.missing) return el("span", { class: "badge badge-staged", text: "Added after setup" });
  return null;
}

function matches(rb, q) {
  if (!q) return true;
  const i = info.get(rb.id);
  return (rb.title + " " + rb.id + " " + ((i && i.haystack) || "")).toLowerCase().includes(q);
}

function renderList() {
  const q = ui.search.value.trim().toLowerCase();
  const shown = items.filter((rb) => matches(rb, q));
  clear(ui.list);
  setText(ui.count, shown.length === items.length ? items.length + " runbooks" : shown.length + " of " + items.length + " runbooks");
  if (!shown.length) {
    const row = el("li", { class: "list-empty" });
    if (!items.length) {
      row.appendChild(el("span", { text: "No runbooks loaded. " }));
      row.appendChild(el("button", { type: "button", class: "btn btn-secondary", text: "Try again", on: { click: () => loadIndex() } }));
    } else {
      row.textContent = "No runbook matches your search. Try a shorter word.";
    }
    ui.list.appendChild(row);
    return;
  }
  shown.forEach((rb) => {
    const i = info.get(rb.id);
    const row = el(
      "button",
      {
        type: "button",
        class: "list-row runbook-row",
        "aria-current": rb.id === selectedId ? "true" : null,
        on: { click: () => select(rb.id, { focus: true }) }
      },
      el("span", { class: "list-row-top" }, el("span", { class: "list-row-title", text: rb.title }), badgeFor(rb.id)),
      el("span", { class: "list-row-meta mono", text: rb.id }),
      i && i.short ? el("span", { class: "runbook-short", text: i.short }) : null
    );
    ui.list.appendChild(el("li", null, row));
  });
}

async function readInto(id) {
  const res = await runbookText(id);
  if (id !== selectedId) return; // another runbook was picked while this loaded
  clear(ui.readerBody);
  if (!res.ok) {
    ui.readerBody.appendChild(el("p", { class: "text-2", role: "alert", text: failedMessage(res) }));
    if (res.reason === "failed") {
      ui.readerBody.appendChild(el("div", null, el("button", { type: "button", class: "btn btn-secondary", text: "Try again", on: { click: () => select(id, {}) } })));
    }
    return;
  }
  const { meta, body } = parseFrontMatter(res.text);
  clear(ui.readerTags);
  (Array.isArray(meta.tags) ? meta.tags : []).forEach((t) => ui.readerTags.appendChild(el("li", { class: "badge", text: t })));
  ui.readerBody.appendChild(renderMarkdown(body, { headingOffset: 1 }));
}

function select(id, { focus = false } = {}) {
  const rb = items.find((r) => r.id === id);
  if (!rb) return;
  selectedId = id;
  setText(ui.readerTitle, rb.title);
  setText(ui.readerId, rb.id);
  show(ui.readerAdded, isSessionRunbook(id));
  clear(ui.readerTags);
  clear(ui.readerBody).appendChild(el("p", { class: "t-sm text-3", text: "Loading runbook text…" }));
  show(ui.readerEmpty, false);
  show(ui.readerContent, true);
  ui.layout.dataset.reading = "true";
  renderList();
  readInto(id);
  if (focus && !wide()) {
    window.scrollTo(0, 0);
    ui.readerTitle.focus({ preventScroll: true });
  }
}

function back() {
  ui.layout.dataset.reading = "false";
  const row = ui.list.querySelector('[aria-current="true"]') || ui.list.querySelector("button");
  if (row) row.focus();
}

// Reads every runbook once so the list can show a short line and search the text.
async function prefetch() {
  if (prefetching || !items.length) return;
  prefetching = true;
  await Promise.all(
    items.map(async (rb) => {
      const res = await runbookText(rb.id);
      if (res.ok) {
        const { meta, body } = parseFrontMatter(res.text);
        info.set(rb.id, { short: shortLine(res.text), haystack: (Array.isArray(meta.tags) ? meta.tags.join(" ") : "") + " " + body });
      } else if (res.reason === "missing") {
        info.set(rb.id, { missing: true });
      }
    })
  );
  prefetching = false;
  renderList();
}

export async function loadIndex() {
  setStatus("loading", "Loading runbooks…");
  const [health, list] = await Promise.all([get("/health"), get("/runbooks")]);
  if (!health.ok || !list.ok || !Array.isArray(list.data)) {
    setStatus("error", "Runbooks failed to load.");
    renderList();
    return false;
  }
  items = list.data.filter((rb) => rb && typeof rb.id === "string" && typeof rb.title === "string");
  state.runbookTitles.clear();
  items.forEach((rb) => state.runbookTitles.set(rb.id, rb.title));
  const n = health.data.runbooks_loaded || items.length;
  setStatus("loaded", n + " runbooks loaded");
  setText(byId("empty-runbook-count"), String(n));
  renderList();
  if (viewShown) prefetch();
  applyPending();
  return true;
}

// Loads the index once if it is not loaded yet.
export function ensureIndex() {
  if (state.runbookTitles.size > 0) return Promise.resolve(true);
  if (!loading) loading = loadIndex().finally(() => (loading = null));
  return loading;
}

// "Open in Runbooks" from a triage result sets state.openRunbook. On a wide
// screen the first runbook opens by itself so the reader is not empty.
function applyPending() {
  if (!items.length) return;
  if (state.openRunbook && items.some((r) => r.id === state.openRunbook)) {
    const id = state.openRunbook;
    state.openRunbook = null;
    select(id, { focus: true });
  } else if (!selectedId && wide()) {
    select(items[0].id, {});
  }
}

export function onRunbooksShown() {
  viewShown = true;
  prefetch();
  applyPending();
}

export function initRunbooks() {
  ui = {
    status: byId("index-status"),
    statusText: byId("index-status-text"),
    retry: byId("index-retry-btn"),
    list: byId("runbook-list"),
    search: byId("runbook-search"),
    count: byId("runbook-count"),
    layout: byId("runbooks-layout"),
    back: byId("runbook-back"),
    readerEmpty: byId("reader-empty"),
    readerContent: byId("reader-content"),
    readerTitle: byId("reader-title"),
    readerId: byId("reader-id"),
    readerAdded: byId("reader-added"),
    readerTags: byId("reader-tags"),
    readerBody: byId("reader-body")
  };
  ui.retry.addEventListener("click", () => loadIndex());
  ui.search.addEventListener("input", renderList);
  ui.back.addEventListener("click", back);
  on("index-changed", () => loadIndex());
  loadIndex();
}
