// Integrations: 12 PSA and RMM connectors. Staged, not live.

import { el, byId, clear, setText, badge, notice } from "../dom.js";
import { get, post, put, del } from "../api.js";
import { connectorStatus } from "../copy.js";
import { copyButton } from "../clipboard.js";
import { toast } from "../toast.js";
import { emit } from "../store.js";

let ui = {};
let providers = [];
let selectedId = null;
let category = "all";
let loaded = false;

function selected() {
  return providers.find((p) => p.id === selectedId) || null;
}

function feedback(kind, title, detail) {
  clear(ui.feedback);
  if (kind) ui.feedback.appendChild(notice(kind === "ok" ? "ok" : "danger", title, detail));
}

function statusBadge(status) {
  return badge(connectorStatus(status), status === "staged" ? "staged" : null);
}

function renderList() {
  clear(ui.list);
  const q = ui.search.value.trim().toLowerCase();
  const shown = providers.filter((p) => {
    if (category !== "all" && p.category !== category) return false;
    if (!q) return true;
    return (p.name + " " + p.protocol + " " + p.category + " " + p.description).toLowerCase().includes(q);
  });
  if (!shown.length) {
    ui.list.appendChild(el("li", { class: "list-empty", text: "No connector matches the filter." }));
    return;
  }
  shown.forEach((p) => {
    const row = el(
      "button",
      {
        type: "button",
        class: "list-row",
        "aria-pressed": p.id === selectedId ? "true" : "false",
        on: {
          click: () => {
            selectedId = p.id;
            feedback(null);
            renderList();
            renderDetail();
          }
        }
      },
      el("span", { class: "list-row-top" }, el("span", { class: "list-row-title", text: p.name }), statusBadge(p.status)),
      el("span", { class: "list-row-meta", text: (p.category === "rmm" ? "RMM" : "PSA") + " · " + p.protocol })
    );
    ui.list.appendChild(el("li", null, row));
  });
}

function renderDetail() {
  const p = selected();
  if (!p) return;
  setText(ui.name, p.name);
  setText(ui.protocol, (p.category === "rmm" ? "RMM platform" : "PSA / ticketing") + " · " + p.protocol);
  ui.status.replaceWith((ui.status = statusBadge(p.status)));
  ui.status.id = "cfg-provider-status";
  setText(ui.desc, p.description || "");
  clear(ui.caps);
  (p.capabilities || []).forEach((cap) => ui.caps.appendChild(el("li", { class: "badge", text: cap })));
  setText(ui.webhook, window.location.origin + (p.webhook_path || "/integrations/webhooks/" + p.id));
  setText(ui.updated, p.updated_at ? "Saved " + p.updated_at : "Not saved yet");
  ui.syncMode.value = p.sync_mode || "draft_internal_note";
  ui.enabled.checked = Boolean(p.enabled);

  clear(ui.fields);
  const values = p.configured_values || {};
  const secrets = p.has_saved_secrets || {};
  (Array.isArray(p.fields) ? p.fields : []).forEach((f) => {
    const id = "cfg-input-" + p.id + "-" + f.key;
    const tag = f.field_type === "secret" && secrets[f.key] ? "Secret saved" : f.required ? "Required" : "Optional";
    const input = el("input", {
      id,
      class: "input" + (f.field_type === "url" ? " mono" : ""),
      type: f.field_type === "secret" ? "password" : f.field_type === "url" ? "url" : "text",
      placeholder: f.placeholder || "",
      autocomplete: "off",
      spellcheck: "false",
      "data-field-key": f.key,
      "aria-describedby": id + "-help"
    });
    input.value = values[f.key] || "";
    ui.fields.appendChild(
      el(
        "div",
        { class: "field" + (f.field_type === "url" ? " field-wide" : "") },
        el("div", { class: "cluster field-top" }, el("label", { class: "field-label", for: id, text: f.label }), el("span", { class: "t-xs text-3", text: tag })),
        input,
        el("p", { class: "field-help", id: id + "-help", text: f.help_text || "" })
      )
    );
  });
}

function formValues() {
  const values = {};
  ui.fields.querySelectorAll("[data-field-key]").forEach((input) => {
    values[input.getAttribute("data-field-key")] = input.value.trim();
  });
  return values;
}

function replace(view) {
  providers = providers.map((p) => (p.id === view.id ? view : p));
  renderList();
  renderDetail();
}

async function load() {
  const res = await get("/integrations");
  if (!res.ok || !Array.isArray(res.data) || !res.data.length) {
    clear(ui.list).appendChild(el("li", { class: "list-empty", text: res.message || "No connectors." }));
    return;
  }
  loaded = true;
  providers = res.data;
  if (!selected()) selectedId = providers[0].id;
  renderList();
  renderDetail();
}

async function busy(btn, fn) {
  btn.disabled = true;
  try {
    await fn();
  } finally {
    btn.disabled = false;
  }
}

export function initIntegrations() {
  ui = {
    list: byId("integration-provider-list"),
    search: byId("integration-search-input"),
    catBar: byId("integration-category-bar"),
    name: byId("cfg-provider-name"),
    protocol: byId("cfg-provider-protocol"),
    status: byId("cfg-provider-status"),
    desc: byId("cfg-provider-desc"),
    caps: byId("cfg-provider-capabilities"),
    webhook: byId("cfg-webhook-url"),
    updated: byId("cfg-updated-at"),
    form: byId("integration-config-form"),
    syncMode: byId("cfg-sync-mode"),
    enabled: byId("cfg-enabled-checkbox"),
    fields: byId("cfg-fields-grid"),
    feedback: byId("cfg-feedback"),
    reset: byId("cfg-reset-btn"),
    test: byId("cfg-test-btn"),
    save: byId("cfg-save-btn"),
    fillDemo: byId("cfg-fill-demo-btn")
  };

  const oldCopy = byId("cfg-copy-webhook-btn");
  const copyBtn = copyButton(() => ui.webhook.textContent || "", { label: "Copy URL", ariaLabel: "Copy webhook URL" });
  copyBtn.id = "cfg-copy-webhook-btn";
  oldCopy.replaceWith(copyBtn);

  ui.catBar.addEventListener("change", (e) => {
    category = e.target.value || "all";
    renderList();
  });
  ui.search.addEventListener("input", renderList);

  ui.fillDemo.addEventListener("click", () => {
    const p = selected();
    if (!p) return;
    (p.fields || []).forEach((f) => {
      const input = ui.fields.querySelector('[data-field-key="' + CSS.escape(f.key) + '"]');
      if (input) input.value = f.field_type === "secret" ? "demo_secret_" + p.id + "_token" : f.placeholder || "demo_value";
    });
    ui.enabled.checked = true;
    feedback("ok", "Demo values filled in", "Select Save settings to mark " + p.name + " as ready (staged).");
  });

  ui.test.addEventListener("click", () =>
    busy(ui.test, async () => {
      const p = selected();
      if (!p) return;
      feedback(null);
      const res = await post("/integrations/" + encodeURIComponent(p.id) + "/test", { sync_mode: ui.syncMode.value, values: formValues() });
      if (!res.ok) feedback("error", "The check failed.", res.detail || res.message);
      else if (res.data.ok) feedback("ok", "Settings look complete (staged check).", res.data.message);
      else feedback("error", "Settings are not complete.", res.data.message);
    })
  );

  ui.form.addEventListener("submit", (e) => {
    e.preventDefault();
    busy(ui.save, async () => {
      const p = selected();
      if (!p) return;
      feedback(null);
      const res = await put("/integrations/" + encodeURIComponent(p.id), { enabled: ui.enabled.checked, sync_mode: ui.syncMode.value, values: formValues() });
      if (!res.ok) {
        feedback("error", "Settings were not saved.", res.detail || res.message);
        return;
      }
      replace(res.data);
      const line =
        res.data.status === "staged" ? "The connector is ready (staged). Nothing is sent." : res.data.status === "paused" ? "Draft settings saved. The connector is paused." : "Settings cleared.";
      feedback("ok", "Settings saved for " + res.data.name, line);
      toast("Settings saved");
      emit("queue-changed");
    });
  });

  ui.reset.addEventListener("click", () =>
    busy(ui.reset, async () => {
      const p = selected();
      if (!p) return;
      feedback(null);
      const res = await del("/integrations/" + encodeURIComponent(p.id));
      if (!res.ok) {
        feedback("error", "The reset failed.", res.detail || res.message);
        return;
      }
      replace(res.data);
      feedback("ok", "Settings reset", res.data.name + " is not set up now.");
      emit("queue-changed");
    })
  );
}

export function onIntegrationsShown() {
  if (!loaded) load();
}
