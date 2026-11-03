// Triage result (docs/design-plan.md sections 5 and 6).
// Order: verdict strip, likely cause, steps, commands, RMM check box,
// source runbooks, escalation, Details, writeback bar.
// The skeleton is <template id="result-template"> in index.html; this module
// clones it and fills it with textContent only.

import { el, clear, setText, show, notice, icon, ICONS } from "../dom.js";
import { post } from "../api.js";
import { state, emit, loadJSON, saveJSON } from "../store.js";
import { risk, confidence, countsLine, modelName, capital, verdict, NOT_RUN } from "../copy.js";
import { copyButton } from "../clipboard.js";
import { runbookText, failedMessage } from "../runbook-text.js";
import { parseFrontMatter, renderMarkdown } from "../markdown.js";
import { toast } from "../toast.js";

const TICKS_PREFIX = "rbp_ticks_";

export function resetResult(container) {
  clear(container);
}

function hashText(text) {
  let h = 0;
  for (let i = 0; i < text.length; i += 1) h = (h * 31 + text.charCodeAt(i)) | 0;
  return "local-" + (h >>> 0).toString(36);
}

/* ---------- Verdict strip + hint ---------- */

function fillVerdict(slot, data, roCount, naCount, matchedCount) {
  const v = verdict(data, naCount);
  const c = confidence(data.confidence);
  const filled = { low: 1, medium: 2, high: 3 }[c.level];
  slot("verdict").dataset.state = v.variant;
  setText(slot("verdict-word"), v.word);
  // Escalate can mean "no runbook covers it" or "a matched runbook says to escalate".
  let sub = countsLine(roCount, naCount);
  if (data.escalate) sub = matchedCount ? sub + ". The runbook says to escalate." : "No runbook covers this ticket. Send it to Tier 3.";
  setText(slot("verdict-sub"), sub);
  const meter = slot("meter");
  meter.setAttribute("aria-label", filled + " of 3");
  meter.querySelectorAll(".meter-seg").forEach((seg, i) => seg.toggleAttribute("data-on", i < filled));
  setText(
    slot("matched-count"),
    matchedCount === 0 ? "No runbook matched" : matchedCount + (matchedCount === 1 ? " runbook matched" : " runbooks matched")
  );
}

function fillHint(slot, data, matchedCount) {
  const hint = slot("hint");
  const safety = el("a", { href: "#safety", class: "link-target", text: "Test a command in the Safety lab" });
  if (data.escalate && matchedCount === 0) {
    hint.append("Next: draft a runbook below, or", safety);
    return;
  }
  hint.append("Next:");
  const voip = el("button", {
    type: "button",
    class: "link-target link-btn",
    text: "Try the uncovered VoIP sample",
    on: { click: () => emit("pick-sample", "escalate") }
  });
  hint.append(voip, safety);
}

/* ---------- Steps checklist (ticks in localStorage by request ID) ---------- */

function fillSteps(root, slot, steps, key) {
  const list = root.querySelector("#steps-list");
  const done = slot("steps-done");
  show(slot("no-steps"), steps.length === 0);
  show(slot("steps-note"), steps.length > 0);
  if (!steps.length) return;

  const stored = loadJSON(key, []);
  const ticks = new Set(Array.isArray(stored) ? stored.filter((n) => Number.isInteger(n) && n < steps.length) : []);
  const update = () => setText(done, ticks.size + " of " + steps.length + " done");

  steps.forEach((text, i) => {
    const item = el("li", { class: "check-item" });
    const box = el("input", {
      type: "checkbox",
      class: "check-box",
      checked: ticks.has(i),
      on: {
        change: () => {
          if (box.checked) ticks.add(i);
          else ticks.delete(i);
          item.toggleAttribute("data-done", box.checked);
          saveJSON(key, [...ticks].sort((a, b) => a - b));
          update();
        }
      }
    });
    item.toggleAttribute("data-done", ticks.has(i));
    item.appendChild(
      el(
        "label",
        { class: "check-step" },
        box,
        el("span", { class: "step-num tabular", "aria-hidden": "true", text: String(i + 1) }),
        el("span", { class: "step-text", text })
      )
    );
    list.appendChild(item);
  });
  update();
}

/* ---------- RMM telemetry (sample data, inside Details) ---------- */

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

/* ---------- Details (collapsed) ---------- */

function fillDetails(root, slot, data, meta, commands) {
  const mode = capital(meta.reasoningMode || "standard") + (meta.vision ? " + screenshot" : "") + (meta.rmmLoop ? " + RMM output" : "");
  setText(slot("d-request"), meta.requestId || "Not sent");
  setText(slot("d-model"), modelName(meta.metaModel));
  setText(slot("d-mode"), mode);
  setText(slot("d-time"), meta.elapsedSeconds + " s");
  setText(
    slot("d-overrides"),
    meta.safetyOverrides > 0
      ? "Safety rules changed " + meta.safetyOverrides + (meta.safetyOverrides === 1 ? " command" : " commands") + " to needs_approval."
      : "None. Safety rules checked every command."
  );
  const roRaw = commands.filter((c) => c.risk === "read_only").length;
  const naRaw = commands.length - roRaw;
  setText(slot("d-raw"), "read_only × " + roRaw + ", needs_approval × " + naRaw + ", escalate: " + Boolean(data.escalate));

  const scores = Object.entries(meta.bm25Scores || {})
    .filter(([, v]) => typeof v === "number")
    .sort((a, b) => b[1] - a[1]);
  const list = slot("d-scores");
  if (!scores.length) list.appendChild(el("li", { class: "text-3", text: "No scores sent." }));
  scores.forEach(([id, score]) =>
    list.appendChild(el("li", { class: "score-row" }, el("span", { class: "mono wrap-anywhere", text: id }), el("span", { class: "tabular", text: score.toFixed(2) })))
  );
  fillTelemetry(root, slot, state.activeQueueItem && state.activeQueueItem.device);
}

/* ---------- Source runbooks ---------- */

// Fills one source box with the runbook text. Tries again on a failed load.
async function fillSourceText(box, id) {
  clear(box).appendChild(el("p", { class: "t-sm text-3", role: "status", text: "Loading runbook text…" }));
  const res = await runbookText(id);
  clear(box);
  if (!res.ok) {
    box.appendChild(
      el(
        "div",
        { class: "stack" },
        el("p", { class: "t-sm text-2", role: "alert", text: failedMessage(res) }),
        res.reason === "failed"
          ? el("div", null, el("button", { type: "button", class: "btn btn-secondary", text: "Try again", on: { click: () => fillSourceText(box, id) } }))
          : null
      )
    );
    return;
  }
  const { body } = parseFrontMatter(res.text);
  box.appendChild(renderMarkdown(body, { headingOffset: 2 }));
}

function fillSources(root, slot, matched, meta) {
  const list = root.querySelector("#matched-runbooks-list");
  show(slot("no-runbooks"), matched.length === 0);
  const ranked = Object.entries(meta.bm25Scores || {})
    .sort((a, b) => b[1] - a[1])
    .map(([id]) => id);
  matched.forEach((id, i) => {
    const title = state.runbookTitles.get(id) || id;
    const rank = ranked.indexOf(id);
    const text = el("div", { class: "source-text" });
    const body = el(
      "div",
      { class: "source-body stack" },
      el(
        "dl",
        { class: "kv" },
        el("div", null, el("dt", { text: "Runbook ID" }), el("dd", { class: "mono wrap-anywhere", text: id })),
        el("div", null, el("dt", { text: "Search rank" }), el("dd", { text: rank >= 0 ? rank + 1 + " of " + ranked.length : "Picked by the model" }))
      ),
      text,
      el("p", { class: "t-sm" }, el("a", { href: "#runbooks", class: "link-target", text: "Open in Runbooks", on: { click: () => (state.openRunbook = id) } }))
    );
    const details = el(
      "details",
      { class: "disclosure source" },
      el(
        "summary",
        null,
        el("span", { class: "source-title", text: title }),
        i === 0 && matched.length > 1 ? el("span", { class: "badge", text: "Best match" }) : null
      ),
      body
    );
    // The text loads on the first open, then stays in the page.
    let started = false;
    details.addEventListener("toggle", () => {
      if (!details.open || started) return;
      started = true;
      fillSourceText(text, id);
    });
    list.appendChild(details);
  });
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

function wireEscalation(root, slot, data, send, matchedCount) {
  const panel = root.querySelector("#escalate-banner");
  if (!data.escalate) return show(panel, false);
  show(panel, true);
  setText(slot("escalate-reason"), data.escalate_reason || "No runbook covers this ticket.");
  setText(
    slot("escalate-help"),
    matchedCount
      ? "Flag the ticket for Tier 3. You can also draft a runbook for this case."
      : "Draft a runbook so the next ticket like this is covered, or flag the ticket for Tier 3."
  );
  root.querySelector("#btn-escalate-flag").addEventListener("click", () => send("escalate"));

  const draftBtn = root.querySelector("#btn-draft-runbook");
  const addBtn = root.querySelector("#btn-hot-index-runbook");
  const draftPanel = root.querySelector("#runbook-draft-panel");
  // Resolve slots now: the fragment is empty once it is in the page.
  const status = slot("draft-status");
  const draftId = slot("draft-id");
  const draftMd = slot("draft-markdown");
  const checked = slot("draft-checked");
  let draft = null;

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
      draft = null;
      setText(draftId, "Draft failed");
      show(checked, false);
      setText(status, "The runbook draft failed. " + res.message);
      setText(draftMd, "");
      show(addBtn, false);
      return;
    }
    const d = res.data;
    draft = { id: d.id, markdown: d.markdown || "" };
    setText(draftId, d.id);
    show(checked, true);
    const checks = d.checks ? d.checks.length : 0;
    const fixes = d.fixes ? d.fixes.length : 0;
    setText(
      status,
      "Drafted “" + d.title + "” with " + checks + (checks === 1 ? " read-only check and " : " read-only checks and ") + fixes + (fixes === 1 ? " change that needs approval." : " changes that need approval.")
    );
    setText(draftMd, draft.markdown);
    show(addBtn, true);
    toast("Runbook drafted");
  });

  addBtn.addEventListener("click", async () => {
    if (!draft) return;
    addBtn.disabled = true;
    setText(addBtn, "Adding runbook…");
    const res = await post("/runbooks/index", { markdown: draft.markdown });
    addBtn.disabled = false;
    setText(addBtn, "Add this runbook and re-run triage");
    if (!res.ok) {
      setText(status, "The runbook was not added. " + res.message);
      return;
    }
    state.draftMarkdown.set((res.data && res.data.id) || draft.id, draft.markdown);
    setText(status, res.data.message || "Runbook added.");
    toast("Runbook added. Re-running triage.");
    emit("index-changed");
    emit("retriage");
  });
}

/* ---------- RMM check box (visible below commands; owner tweak 1) ---------- */

function wireRmmCheck(root, show_) {
  const panel = root.querySelector("#rmm-check-panel");
  const output = root.querySelector("#rmm-check-output");
  const btn = root.querySelector("#btn-rmm-retriage");
  const err = el("p", { class: "field-error", role: "alert", hidden: true });
  btn.parentNode.after(err);
  show(panel, show_);
  output.addEventListener("input", () => show(err, false));
  btn.addEventListener("click", () => {
    const text = output.value.trim();
    if (!text) {
      setText(err, "Paste RMM output first, or stage an RMM check above.");
      show(err, true);
      output.focus();
      return;
    }
    emit("rmm-retriage", { output: text, command: "Check results from RMM" });
  });
  // Staged RMM checks add their sample output here.
  return (cmd, text) => {
    const block = "# " + cmd + "\n" + text.trim();
    output.value = output.value.trim() ? output.value.trim() + "\n\n" + block : block;
    show(err, false);
  };
}

/* ---------- Command block (the one bold element) ---------- */

async function dispatchRmm(cmd, approved, note, out, trigger, addOutput) {
  const isRo = cmd.risk === "read_only";
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
  clear(out);
  show(out, true);
  if (!res.ok) {
    out.appendChild(notice("danger", "The RMM job was not staged.", res.message));
    return false;
  }
  const output = res.data.simulated_output || "";
  out.append(
    el("p", { class: "t-xs text-3" }, el("span", { class: "badge badge-staged", text: "Sample data" }), " Staged job " + res.data.job_id + ". Not run on a device."),
    output ? el("pre", { class: "code rmm-output", text: output }) : null,
    output ? el("p", { class: "t-xs text-3", text: "Output added to “Check results from RMM” below." }) : null
  );
  if (output) addOutput(cmd.command, output);
  setText(trigger, isRo ? "RMM check staged" : "Change request staged");
  toast(isRo ? "RMM check staged" : "RMM change request staged");
  return true;
}

function commandBlock(cmd, addOutput) {
  const r = risk(cmd.risk);
  const isRo = cmd.risk === "read_only";
  const code = el("code", { text: cmd.command || "" });
  const pre = el("pre", { class: "cmd-code" }, el("span", { class: "cmd-prompt", "aria-hidden": "true", text: "PS> " }), code);
  const live = el("span", { class: "sr-only", "aria-live": "polite" });
  let block = null;
  const copyBtn = copyButton(() => cmd.command || "", {
    ariaLabel: "Copy command",
    liveRegion: live,
    liveText: "Command copied",
    onFail: () => {
      const range = document.createRange();
      range.selectNodeContents(code);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    },
    onDone: (ok) => {
      if (!ok || !block) return;
      block.classList.remove("cmd-pulse");
      void block.offsetWidth;
      block.classList.add("cmd-pulse");
    }
  });
  copyBtn.classList.add("cmd-copy");
  const rmmBtn = el("button", { type: "button", class: "btn btn-secondary btn-sm", text: isRo ? "Stage RMM check" : "Stage RMM change request" });
  const out = el("div", { class: "stack cmd-out", hidden: true });

  const body = el(
    "div",
    { class: "cmd-body" },
    el("div", { class: "cmd-head" }, el("p", { class: "cmd-purpose", text: cmd.purpose || "" }), copyBtn),
    pre,
    el("div", { class: "cmd-foot" }, el("span", { class: "cmd-note", text: NOT_RUN }), rmmBtn)
  );
  block = el(
    "article",
    { class: "cmd cmd-" + r.variant, "aria-label": isRo ? "Read-only command" : "Command that changes the system. Needs approval." },
    el("span", { class: "cmd-tab" }, icon(isRo ? ICONS.eye : ICONS.hand, 14), el("span", { text: r.word })),
    body,
    live
  );

  if (isRo) {
    rmmBtn.addEventListener("click", () => dispatchRmm(cmd, false, null, out, rmmBtn, addOutput));
  } else {
    const noteId = "approval-" + Math.random().toString(36).slice(2, 8);
    const noteInput = el("input", { type: "text", id: noteId, class: "input", placeholder: "For example CHG-1042" });
    const confirm = el("button", { type: "button", class: "btn btn-primary btn-sm", text: "Approve and stage" });
    const cancel = el("button", { type: "button", class: "btn btn-quiet btn-sm", text: "Cancel" });
    const drawer = el(
      "div",
      { class: "stack cmd-approval", hidden: true },
      el("label", { class: "field-label", for: noteId, text: "Change ID or approval note" }),
      el("p", { class: "field-help", text: "A technician must approve this change before it is staged in the RMM." }),
      el("div", { class: "cmd-approval-row" }, noteInput, confirm, cancel)
    );
    rmmBtn.setAttribute("aria-expanded", "false");
    rmmBtn.addEventListener("click", () => {
      drawer.hidden = !drawer.hidden;
      rmmBtn.setAttribute("aria-expanded", drawer.hidden ? "false" : "true");
      if (!drawer.hidden) noteInput.focus();
    });
    cancel.addEventListener("click", () => {
      show(drawer, false);
      rmmBtn.setAttribute("aria-expanded", "false");
      rmmBtn.focus();
    });
    confirm.addEventListener("click", async () => {
      const note = noteInput.value.trim();
      if (!note) {
        clear(out);
        show(out, true);
        out.appendChild(el("p", { class: "field-error", role: "alert", text: "Enter a change ID or approval note first." }));
        noteInput.focus();
        return;
      }
      if (await dispatchRmm(cmd, true, note, out, rmmBtn, addOutput)) {
        show(drawer, false);
        rmmBtn.setAttribute("aria-expanded", "false");
      }
    });
    body.appendChild(drawer);
  }
  body.appendChild(out);
  return block;
}

function fillCommands(root, slot, commands, escalate, addOutput) {
  const section = slot("commands-section");
  const ro = commands.filter((c) => c.risk === "read_only");
  const na = commands.filter((c) => c.risk !== "read_only");
  // Escalated tickets with no commands: the escalation panel replaces the group.
  show(section, commands.length > 0 || !escalate);
  setText(slot("cmd-counts"), commands.length ? countsLine(ro.length, na.length) : "");
  if (!commands.length) setText(slot("never-runs"), "No commands for this ticket.");
  show(slot("ro-title"), ro.length > 0);
  setText(slot("ro-title"), "Read-only (" + ro.length + ")");
  ro.forEach((c) => slot("ro-list").appendChild(commandBlock(c, addOutput)));
  const warning = root.querySelector("#approval-warning-banner");
  show(warning, na.length > 0);
  slot("approval-title").prepend(icon(ICONS.warn, 16), " ");
  setText(
    slot("approval-text"),
    "Check the scope and get approval before you run " + (na.length === 1 ? "this command." : "these " + na.length + " commands.")
  );
  na.forEach((c) => slot("na-list").appendChild(commandBlock(c, addOutput)));
}

/* ---------- Render ---------- */

export function renderResult(container, data, meta) {
  state.lastResult = data;
  clear(container);
  const root = document.getElementById("result-template").content.cloneNode(true);
  const slot = (name) => root.querySelector('[data-slot="' + name + '"]');

  const commands = (Array.isArray(data.commands) ? data.commands : []).filter((c) => c && typeof c.command === "string");
  const ro = commands.filter((c) => c.risk === "read_only");
  const matched = Array.isArray(data.matched_runbooks) ? data.matched_runbooks : [];
  const steps = Array.isArray(data.steps) ? data.steps : [];

  // Resolve every slot before the fragment goes into the page.
  setText(root.querySelector("#confidence-badge"), confidence(data.confidence).text);
  fillVerdict(slot, data, ro.length, commands.length - ro.length, matched.length);
  fillHint(slot, data, matched.length);
  setText(root.querySelector("#likely-cause-text"), capital(data.likely_cause || ""));
  fillSteps(root, slot, steps, TICKS_PREFIX + (meta.requestId || hashText(steps.join("\n"))));
  const addOutput = wireRmmCheck(root, commands.length > 0);
  fillCommands(root, slot, commands, Boolean(data.escalate), addOutput);
  fillSources(root, slot, matched, meta);
  const send = wireWriteback(root, slot, data);
  wireEscalation(root, slot, data, send, matched.length);
  fillDetails(root, slot, data, meta, commands);

  container.appendChild(root);
  container.classList.remove("reveal");
  void container.offsetWidth;
  container.classList.add("reveal");
}
