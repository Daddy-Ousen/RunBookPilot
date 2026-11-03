// Runbook source text. The 18 shipped runbooks are static copies in
// /static/runbooks/ (index.json maps a runbook ID to its file). A runbook added
// in this session keeps its in-session text (state.draftMarkdown).
// Nothing here changes the API. Phase 6 checks the copies match data/runbooks/.

import { state } from "./store.js";

const BASE = "/static/runbooks/";
const cache = new Map(); // id -> text
let fileMap = null; // { id: "file.md" }, kept only after a good load
let mapLoading = null;

async function loadMap() {
  if (fileMap) return fileMap;
  if (!mapLoading) {
    mapLoading = fetch(BASE + "index.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then((data) => {
        fileMap = data && typeof data === "object" ? data : {};
        return fileMap;
      })
      .finally(() => {
        mapLoading = null;
      });
  }
  return mapLoading;
}

// True when this ID was added in this browser session.
export function isSessionRunbook(id) {
  return state.draftMarkdown.has(id);
}

// Resolves { ok, text, source } or { ok: false, reason: "missing" | "failed", detail }.
export async function runbookText(id) {
  if (state.draftMarkdown.has(id)) return { ok: true, text: state.draftMarkdown.get(id), source: "session" };
  if (cache.has(id)) return { ok: true, text: cache.get(id), source: "static" };
  let map;
  try {
    map = await loadMap();
  } catch (err) {
    return { ok: false, reason: "failed", detail: (err && err.message) || "Network error" };
  }
  const file = map[id];
  if (typeof file !== "string" || !/^[\w.-]+\.md$/.test(file)) return { ok: false, reason: "missing" };
  try {
    const res = await fetch(BASE + encodeURIComponent(file));
    if (!res.ok) return { ok: false, reason: "failed", detail: "HTTP " + res.status };
    const text = await res.text();
    cache.set(id, text);
    return { ok: true, text, source: "static" };
  } catch (err) {
    return { ok: false, reason: "failed", detail: (err && err.message) || "Network error" };
  }
}

export function failedMessage(result) {
  if (result.reason === "missing") return "This runbook has no text in this copy. It was added after setup.";
  return "The runbook text did not load. Check the connection, then try again.";
}
