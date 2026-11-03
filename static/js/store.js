// Safe localStorage access plus the shared in-memory app state.

export function load(key, fallback = null) {
  try {
    const raw = localStorage.getItem(key);
    return raw === null ? fallback : raw;
  } catch (_e) {
    return fallback;
  }
}

export function save(key, value) {
  try {
    if (value === null || value === undefined) localStorage.removeItem(key);
    else localStorage.setItem(key, String(value));
  } catch (_e) {
    /* Storage blocked: ignore */
  }
}

export function loadJSON(key, fallback = null) {
  const raw = load(key);
  if (raw === null) return fallback;
  try {
    return JSON.parse(raw);
  } catch (_e) {
    return fallback;
  }
}

export function saveJSON(key, value) {
  save(key, value === null || value === undefined ? null : JSON.stringify(value));
}

// State shared by the triage input and the result.
export const state = {
  runbookTitles: new Map(),
  queueItems: [],
  activeQueueItem: null,
  stagedOnlyQueue: false,
  lastResult: null,
  lastTicket: "",
  screenshot: null, // { dataUrl, name, caption }
  rmmLoopOutput: null
};

// Tiny event bus between modules.
const listeners = new Map();

export function on(event, fn) {
  if (!listeners.has(event)) listeners.set(event, new Set());
  listeners.get(event).add(fn);
}

export function emit(event, detail) {
  (listeners.get(event) || []).forEach((fn) => fn(detail));
}
