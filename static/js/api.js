// Fetch wrapper. Always resolves; never throws.
// Result: { ok, status, data, headers, requestId, retryAfter, detail, message }

import { errorText } from "./copy.js";

function detailOf(data) {
  if (!data) return "";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail) && data.detail[0] && data.detail[0].msg) return data.detail[0].msg;
  return "";
}

export async function request(path, { method = "GET", body, signal } = {}) {
  const init = { method, signal, headers: {} };
  if (body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(path, init);
  } catch (err) {
    return {
      ok: false,
      status: 0,
      data: null,
      headers: null,
      requestId: null,
      retryAfter: null,
      detail: (err && err.message) || "Network error",
      message: errorText(0)
    };
  }
  let data = null;
  try {
    data = await response.json();
  } catch (_e) {
    data = null;
  }
  const retryRaw = response.headers.get("Retry-After");
  const retryAfter = retryRaw && /^\d+$/.test(retryRaw) ? Number(retryRaw) : null;
  const result = {
    ok: response.ok,
    status: response.status,
    data,
    headers: response.headers,
    requestId: response.headers.get("X-Request-ID"),
    retryAfter,
    detail: detailOf(data),
    message: ""
  };
  if (!response.ok) result.message = errorText(response.status, retryAfter);
  return result;
}

export const get = (path) => request(path);
export const post = (path, body) => request(path, { method: "POST", body });
export const put = (path, body) => request(path, { method: "PUT", body });
export const del = (path) => request(path, { method: "DELETE" });

// Triage metadata travels in response headers.
export function triageMeta(res) {
  const h = res.headers;
  let bm25Scores = {};
  try {
    const raw = h && h.get("X-BM25-Scores");
    if (raw) bm25Scores = JSON.parse(raw);
  } catch (_e) {
    bm25Scores = {};
  }
  return {
    requestId: res.requestId,
    metaModel: h ? h.get("X-Meta-Model") : null,
    reasoningMode: h ? h.get("X-Reasoning-Mode") : null,
    safetyOverrides: Number((h && h.get("X-Safety-Overrides")) || 0),
    bm25Scores
  };
}
