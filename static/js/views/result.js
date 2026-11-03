// Triage result. Phase 2: every old feature, plain layout on the new components.
// The skeleton is <template id="result-template"> in index.html; this module
// clones it and fills it with textContent only.
// Phase 3 replaces the layout (verdict strip, checklist, command blocks, Details).

import { el, clear, setText, show, badge, notice, icon, ICONS } from "../dom.js";
import { post } from "../api.js";
import { state, emit } from "../store.js";
import { risk, confidence, countsLine, modelName, capital, NOT_RUN } from "../copy.js";
import { copyButton } from "../clipboard.js";
import { toast } from "../toast.js";

export function resetResult(container) {
  clear(container);
}

/* ---------- RMM telemetry (sample data) ---------- */

function fillTelemetry(root, slot, device) {
  const panel = root.querySelector("#rmm-telemetry-panel");
  if (!device) return show(panel, false);
  show(panel, true);
  setText(slot("host"), device.hostname || "srv-win-01.corp.example.test");
  setText(slot("agent"), (device.rmm_provider_name || "RMM") + " · " + capital(device.agent_status || "online"));
  setText(slot("os"), device.os_version || "");
  setText(slot("resources"), "CPU " + device.cpu_percent + "% · RAM " + device.memory_percent + "% · " + device.disk_free_gb + " GB free");
  setText(slot("boot"), device.last_boot + " · " + device.ip_address);
  setText(slot("alert"), device.active_alert || "None");
}

/* ---------- Writeback (staged) ---------- */

function wireWriteback(root, slot, data) {
  const select = root.querySelector("#writeback-provider-select");
  const noteBtn = root.querySelector("#btn-writeback-note");
  const flagBtn = root.querySelector("#btn-writeback-escalate");
  const feedback = root.querySelector("#writeback-feedback");
  const item = state.activeQueueItem;
  if (item && item.category === "ticketing") select.value = item.provider_id;
  setText(slot("target"), item ? item.external_ref : "manual-ticket");

  async function send(action) {
    const target = state.activeQueueItem ? state.activeQueueItem.id : "manual-ticket";
    noteBtn.disabled = true;
    flagBtn.disabled = true;
    const res = await post("/integrations/tickets/" + encodeURIComponent(target) + "/writeback", {
      provider_id: select.value || "connectwise_psa",
      action,
      likely_cause: data.likely_cause || "Diagnosis recorded",
      confidence: data.confidence || "medium",
      matched_runbooks: Array.isArray(data.matched_runbooks) ? data.matched_runbooks : [],
      steps: Array.isArray(data.steps) ? data.steps : [],
      commands: Array.isArray(data.commands) ? data.commands : [],
      escalate_reason: data.escalate_reason || null
    });
    noteBtn.disabled = false;
    flagBtn.disabled = false;
    clear(feedback);
    show(feedback, true);
    if (!res.ok) {
      feedback.appendChild(notice("danger", "The note was not staged.", res.detail || res.message));
      return;
    }
    const word = action === "escalate" ? "Flagged for Tier 3 (staged)" : "Note posted (staged)";
    feedback.appendChild(notice("ok", word, res.data.message || ""));
    if (res.data.note_preview) feedback.appendChild(el("pre", { class: "code code-scroll", text: res.data.note_preview }));
    toast(word);
    emit("queue-changed");
  }

  noteBtn.addEventListener("click", () => send("internal_note"));
  flagBtn.addEventListener("click", () => send("escalate"));
  return send;
}

/* ---------- Escalation, draft runbook, add to index ---------- */

function wireEscalation(root, slot, data, send) {
  const panel = root.querySelector("#escalate-banner");
  if (!data.escalate) return show(panel, false);
  show(panel, true);
  setText(slot("escalate-reason"), data.escalate_reason || "No runbook covers this ticket.");
  root.querySelector("#btn-escalate-flag").addEventListener("click", () => send("escalate"));

  const draftBtn = root.querySelector("#btn-draft-runbook");
  const addBtn = root.querySelector("#btn-hot-index-runbook");
  const draftPanel = root.querySelector("#runbook-draft-panel");
  // Resolve slots now: the fragment is empty once it is in the page.
  const status = slot("draft-status");
  const draftId = slot("draft-id");
  const draftMd = slot("draft-markdown");
  let markdown = null;

  draftBtn.addEventListener("click", async () => {
    const ticket = state.lastTicket || "";
    if (!ticket.trim()) return;
    draftBtn.disabled = true;
    draftBtn.setAttribute("aria-busy", "true");
    setText(draftBtn, "Drafting runbook…");
    const res = await post("/runbooks/draft", { ticket, escalate_reason: data.escalate_reason || null });
    draftBtn.disabled = false;
    draftBtn.removeAttribute("aria-busy");
    setText(draftBtn, "Draft a runbook");
    show(draftPanel, true);
    if (!res.ok) {
      markdown = null;
      setText(draftId, "Draft failed");
      setText(status, "The runbook draft failed. " + (res.detail || res.message));
      setText(draftMd, "");
      show(addBtn, false);
      return;
    }
    const d = res.data;
    markdown = d.markdown || "";
    setText(draftId, d.id);
    setText(
      status,
      "Drafted “" + d.title + "” with " + (d.checks ? d.checks.length : 0) + " read-only checks and " + (d.fixes ? d.fixes.length : 0) + ((d.fixes && d.fixes.length === 1) ? " change that needs approval." : " changes that need approval.")
    );
    setText(draftMd, markdown);
    show(addBtn, true);
  });

  addBtn.addEventListener("click", async () => {
    if (!markdown) return;
    addBtn.disabled = true;
    setText(addBtn, "Adding runbook…");
    const res = await post("/runbooks/index", { markdown });
    addBtn.disabled = false;
    setText(addBtn, "Add this runbook and re-run triage");
    if (!res.ok) {
      setText(status, "The runbook was not added. " + (res.detail || res.message));
      return;
    }
    setText(status, res.data.message || "Runbook added.");
    toast("Runbook added");
    emit("index-changed");
    emit("retriage");
  });
}

/* ---------- Commands ---------- */

async function dispatchRmm(cmd, approved, note, out, loopBar, trigger) {
  const device = state.activeQueueItem && state.activeQueueItem.device ? state.activeQueueItem.device : null;
  trigger.disabled = true;
  const res = await post("/integrations/rmm/dispatch", {
    rmm_provider_id: device ? device.rmm_provider_id : "ninjaone_rmm",
    hostname: device ? device.hostname : "srv-win-01.corp.example.test",
    command: cmd.command,
    purpose: cmd.purpose,
    ticket_id: state.activeQueueItem ? state.activeQueueItem.id : "manual-ticket",
    approved_by_technician: approved,
    approval_note: note
  });
  trigger.disabled = false;
  show(out, true);
  if (!res.ok) {
    setText(out, "The RMM job was not staged. " + (res.detail || res.message));
    return false;
  }
  setText(out, res.data.simulated_output || "RMM job staged.");
  if (res.data.simulated_output) {
    loopBar.dataset.output = res.data.simulated_output;
    show(loopBar, true);
  }
  setText(trigger, "Job staged (" + res.data.job_id + ")");
  toast("RMM job staged");
  return true;
}

function commandItem(cmd) {
  const r = risk(cmd.risk);
  const isRo = cmd.risk === "read_only";
  const code = el("pre", { class: "code" }, el("code", { text: cmd.command || "" }));
  const live = el("span", { class: "sr-only", "aria-live": "polite" });
  const copyBtn = copyButton(() => cmd.command || "", {
    ariaLabel: "Copy command",
    liveRegion: live,
    onFail: () => {
      const range = document.createRange();
      range.selectNodeContents(code);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    }
  });
  const rmmBtn = el("button", { type: "button", class: "btn btn-secondary btn-sm", text: isRo ? "Stage RMM check" : "Stage RMM change request" });
  const out = el("pre", { class: "code rmm-output", hidden: true });
  const loopBar = el(
    "div",
    { class: "notice notice-staged", hidden: true },
    el("span", { text: "Use this RMM output to narrow the cause." }),
    el(
      "div",
      { class: "notice-actions" },
      el("button", {
        type: "button",
        class: "btn btn-secondary btn-sm",
        text: "Re-run triage with this output",
        on: { click: () => emit("rmm-retriage", { output: loopBar.dataset.output || out.textContent || "", command: cmd.command }) }
      })
    )
  );

  const item = el(
    "div",
    { class: "cmd cmd-" + r.variant, role: "group", "aria-label": isRo ? "Read-only command" : "Command that changes the system. Needs approval." },
    el(
      "div",
      { class: "cmd-head" },
      el("span", { class: "cmd-purpose", text: cmd.purpose || "" }),
      el("div", { class: "btn-row" }, el("span", { class: "badge badge-" + r.variant }, icon(isRo ? ICONS.eye : ICONS.hand, 14), r.word), rmmBtn, copyBtn)
    ),
    code,
    el("p", { class: "cmd-foot", text: NOT_RUN }),
    live
  );

  if (isRo) {
    rmmBtn.addEventListener("click", () => dispatchRmm(cmd, false, null, out, loopBar, rmmBtn));
  } else {
    const noteInput = el("input", { type: "text", class: "input", placeholder: "Change ID or approval note, for example CHG-1042", "aria-label": "Approval note" });
    const confirm = el("button", { type: "button", class: "btn btn-primary btn-sm", text: "Approve and stage RMM job" });
    const cancel = el("button", { type: "button", class: "btn btn-quiet btn-sm", text: "Cancel" });
    const drawer = el(
      "div",
      { class: "stack cmd-approval", hidden: true },
      el("p", { class: "field-help", text: "A technician must approve this change before it is staged in the RMM." }),
      el("div", { class: "cmd-approval-row" }, noteInput, confirm, cancel)
    );
    rmmBtn.addEventListener("click", () => {
      drawer.hidden = !drawer.hidden;
      if (!drawer.hidden) noteInput.focus();
    });
    cancel.addEventListener("click", () => show(drawer, false));
    confirm.addEventListener("click", async () => {
      const note = noteInput.value.trim();
      if (!note) {
        show(out, true);
        setText(out, "Enter an approval note or change ID first.");
        noteInput.focus();
        return;
      }
      if (await dispatchRmm(cmd, true, note, out, loopBar, rmmBtn)) show(drawer, false);
    });
    item.appendChild(drawer);
  }
  item.append(out, loopBar);
  return item;
}

function fillCommands(root, slot, commands) {
  const ro = commands.filter((c) => c && c.risk === "read_only");
  const na = commands.filter((c) => c && c.risk !== "read_only");
  setText(slot("cmd-counts"), countsLine(ro.length, na.length));
  show(slot("no-commands"), commands.length === 0);
  show(root.querySelector("#commands-list"), commands.length > 0);
  show(slot("ro-title"), ro.length > 0);
  setText(slot("ro-title"), "Read-only (" + ro.length + ")");
  ro.forEach((c) => slot("ro-list").appendChild(commandItem(c)));
  const warning = root.querySelector("#approval-warning-banner");
  show(warning, na.length > 0);
  setText(slot("approval-text"), "Check the scope and get approval before you run " + (na.length === 1 ? "this command." : "these " + na.length + " commands."));
  warning.querySelector(".notice-title").prepend(icon(ICONS.warn, 16), " ");
  na.forEach((c) => slot("na-list").appendChild(commandItem(c)));
}

/* ---------- Render ---------- */

export function renderResult(container, data, meta) {
  state.lastResult = data;
  clear(container);
  const root = document.getElementById("result-template").content.cloneNode(true);
  const slot = (name) => root.querySelector('[data-slot="' + name + '"]');

  // Meta line (moves into Details in Phase 3)
  const mode = capital(meta.reasoningMode || "standard") + (meta.vision ? " + screenshot" : "") + (meta.rmmLoop ? " + RMM output" : "");
  slot("meta").append(
    el("span", { class: "mono", text: "Request " + (meta.requestId || "local") }),
    el("span", { text: modelName(meta.metaModel) + " · " + mode }),
    meta.safetyOverrides > 0 ? badge("Safety rules changed " + meta.safetyOverrides + " command(s) to needs approval", "na") : badge("Safety rules checked every command"),
    el("span", { class: "tabular", text: meta.elapsedSeconds + " s" })
  );

  fillTelemetry(root, slot, state.activeQueueItem && state.activeQueueItem.device);
  const send = wireWriteback(root, slot, data);
  wireEscalation(root, slot, data, send);

  // Likely cause + source runbooks
  setText(root.querySelector("#confidence-badge"), confidence(data.confidence).text);
  setText(root.querySelector("#likely-cause-text"), data.likely_cause || "");
  const scores = meta.bm25Scores || {};
  const matched = Array.isArray(data.matched_runbooks) ? data.matched_runbooks : [];
  const rbList = root.querySelector("#matched-runbooks-list");
  show(slot("no-runbooks"), matched.length === 0);
  matched.forEach((id) =>
    rbList.appendChild(
      el(
        "li",
        { class: "badge" },
        state.runbookTitles.get(id) || id,
        el("span", { class: "mono text-3", text: " " + id + (typeof scores[id] === "number" ? " · BM25L " + scores[id].toFixed(1) : "") })
      )
    )
  );

  // Steps
  const steps = Array.isArray(data.steps) ? data.steps : [];
  const stepList = root.querySelector("#steps-list");
  show(slot("no-steps"), steps.length === 0);
  steps.forEach((s) => stepList.appendChild(el("li", { text: s })));

  fillCommands(root, slot, Array.isArray(data.commands) ? data.commands : []);

  container.appendChild(root);
  container.classList.remove("reveal");
  void container.offsetWidth;
  container.classList.add("reveal");
}
