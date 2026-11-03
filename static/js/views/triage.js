// Triage view: ticket input, samples, mode, screenshot, queue, submit, states.

import { el, byId, clear, setText, show, badge, notice } from "../dom.js";
import { post, get, triageMeta } from "../api.js";
import { state, on, emit } from "../store.js";
import { priority, queueStatus, modelName } from "../copy.js";
import { renderResult, resetResult } from "./result.js";
import { ensureIndex } from "./runbooks.js";

const MAX_CHARS = 4000;
const MAX_SCREENSHOT_BYTES = 1400000;

export const SAMPLES = [
  {
    key: "lockout",
    title: "AD lockout",
    desc: "Event 4740 locks a user every 15 min",
    text: "Standard user user01@corp.example.test changed their password yesterday and now gets 'The referenced account is currently locked out' every 15 minutes. Domain controller dc-01.corp.example.test logged Event ID 4740 from their docked workstation."
  },
  {
    key: "backup",
    title: "VSS backup stall",
    desc: "Nightly image backup times out",
    text: "Alert on srv-app-01.corp.example.test: Last night's scheduled BCDR image backup failed at 02:15 AM with error 0x800423f4 and VSS Event ID 8193 snapshot timeout."
  },
  {
    key: "mail",
    title: "M365 mail queue",
    desc: "Outbound mail delayed",
    text: "Users at tenant-alpha.test report outbound M365 emails to external partners are delayed by 40 minutes and sitting in Deferred status in Exchange Online after a gateway connector change."
  },
  {
    key: "escalate",
    title: "Uncovered VoIP",
    desc: "No runbook covers this (escalates)",
    text: "Desk SIP VoIP handset on PoE switch port Gi1/0/24 is stuck in a TFTP firmware bootloop and failing LLDP-MED voice VLAN 120 negotiation."
  }
];

const SAMPLE_SHOTS = {
  rdp: {
    title: "Remote Desktop Connection (mstsc.exe)",
    code: "Error 0x80070005 / CredSSP & TermService Refused",
    detail: "Remote Desktop cannot connect to srv-rds-01.corp.example.test:3389 (TermService stopped)",
    name: "rdp_error_srv-rds-01.png",
    caption: "Windows Remote Desktop dialog showing Error 0x80070005 / TermService stopped on srv-rds-01.corp.example.test port 3389",
    ticket: "Users cannot connect via Remote Desktop (mstsc) to srv-rds-01.corp.example.test after maintenance. See attached error dialog screenshot."
  },
  vss: {
    title: "Windows Server Backup / VSS Writer Monitor",
    code: "BCDR Image Backup Failed: Error 0x800423f4 (Event ID 8193)",
    detail: "Volume Shadow Copy Service writer SqlServerWriter timed out on srv-app-01.corp.example.test",
    name: "vss_writer_0x800423f4.png",
    caption: "Windows Server Backup dialog showing Error 0x800423f4 and VSS Event ID 8193 writer timeout on srv-app-01.corp.example.test",
    ticket: "Nightly image backup failed on srv-app-01.corp.example.test. See attached Windows Server Backup error dialog screenshot."
  }
};

let ui = {};
let activeSampleKey = null;
let timerId = null;
let countdownId = null;
let busy = false;

/* ---------- Ticket box ---------- */

function updateCharCount() {
  const len = ui.ticket.value.length;
  setText(ui.charCount, len + " / " + MAX_CHARS);
  ui.charCount.dataset.level = len >= MAX_CHARS ? "max" : len >= 3500 ? "warn" : "";
}

function setTicket(text) {
  ui.ticket.value = text;
  updateCharCount();
}

/* ---------- Errors ---------- */

function clearError() {
  clear(ui.errorRegion);
  if (countdownId) {
    window.clearInterval(countdownId);
    countdownId = null;
  }
}

// res: api result, or { message } for local validation.
function showError(res) {
  clearError();
  const retryBtn = res.status !== undefined ? el("button", { type: "button", class: "btn btn-secondary btn-sm", text: "Try again", on: { click: () => submitTriage() } }) : null;
  const tech = res.detail || res.requestId
    ? el(
        "details",
        { class: "disclosure" },
        el("summary", { text: "Technical details" }),
        el(
          "div",
          { class: "disclosure-body mono wrap-anywhere" },
          res.status ? el("div", { text: "HTTP " + res.status }) : null,
          res.detail ? el("div", { text: res.detail }) : null,
          res.requestId ? el("div", { text: "Request ID: " + res.requestId }) : null
        )
      )
    : null;
  const box = notice(
    "danger",
    res.message,
    res.status !== undefined ? "Your ticket text is kept." : null,
    retryBtn ? el("div", { class: "notice-actions" }, retryBtn) : null,
    tech
  );
  ui.errorRegion.appendChild(box);

  if (retryBtn && res.retryAfter) {
    let left = res.retryAfter;
    retryBtn.disabled = true;
    setText(retryBtn, "Try again in " + left + " s");
    countdownId = window.setInterval(() => {
      left -= 1;
      if (left <= 0) {
        window.clearInterval(countdownId);
        countdownId = null;
        retryBtn.disabled = false;
        setText(retryBtn, "Try again");
      } else {
        setText(retryBtn, "Try again in " + left + " s");
      }
    }, 1000);
  }
}

/* ---------- Result column states ---------- */

function showState(which) {
  show(ui.empty, which === "empty");
  show(ui.loading, which === "loading");
  show(ui.result, which === "result");
}

function startTimer() {
  const started = performance.now();
  setText(ui.timer, "0.0 s");
  stopTimer();
  timerId = window.setInterval(() => {
    setText(ui.timer, ((performance.now() - started) / 1000).toFixed(1) + " s");
  }, 100);
}

function stopTimer() {
  if (timerId) {
    window.clearInterval(timerId);
    timerId = null;
  }
}

/* ---------- Samples ---------- */

function renderSamples() {
  clear(ui.sampleList);
  SAMPLES.forEach((sample) => {
    const row = el(
      "button",
      {
        type: "button",
        class: "list-row",
        "aria-pressed": activeSampleKey === sample.key ? "true" : "false",
        on: { click: () => pickSample(sample.key) }
      },
      el("span", { class: "list-row-title", text: sample.title }),
      el("span", { class: "list-row-meta", text: sample.desc })
    );
    ui.sampleList.appendChild(el("li", null, row));
  });
}

function pickSample(key) {
  const sample = SAMPLES.find((s) => s.key === key);
  if (!sample) return;
  unlinkQueueItem();
  clearRmmLoop();
  activeSampleKey = key;
  renderSamples();
  setTicket(sample.text);
  clearError();
  ui.ticket.focus();
}

function clearActiveSample() {
  if (activeSampleKey) {
    activeSampleKey = null;
    renderSamples();
  }
}

/* ---------- Screenshot ---------- */

function setScreenshot(dataUrl, name, caption) {
  state.screenshot = { dataUrl, name, caption: caption || name };
  ui.shotThumb.src = dataUrl;
  setText(ui.shotName, name);
  setText(ui.shotCaption, caption || "Sent to the model with the ticket.");
  show(ui.shotPreview, true);
}

function clearScreenshot() {
  state.screenshot = null;
  ui.shotThumb.removeAttribute("src");
  setText(ui.shotName, "");
  setText(ui.shotCaption, "");
  ui.shotInput.value = "";
  show(ui.shotPreview, false);
}

function readScreenshotFile(file) {
  if (!file) return;
  if (!/^image\/(png|jpeg|webp)$/.test(file.type)) {
    showError({ message: "Use a PNG, JPEG or WebP image." });
    return;
  }
  if (file.size > MAX_SCREENSHOT_BYTES) {
    showError({ message: "The screenshot is over 1.4 MB. Choose a smaller image." });
    ui.shotInput.value = "";
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    if (typeof reader.result === "string") {
      setScreenshot(reader.result, file.name, "Uploaded screenshot (" + file.name + ")");
    }
  };
  reader.readAsDataURL(file);
}

// Draws a synthetic Windows error dialog. Sample data only.
function syntheticDialogPng(shot) {
  const canvas = document.createElement("canvas");
  canvas.width = 480;
  canvas.height = 220;
  const ctx = canvas.getContext("2d");
  if (!ctx) return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";
  ctx.fillStyle = "#18181b";
  ctx.fillRect(0, 0, 480, 220);
  ctx.strokeStyle = "#ef4444";
  ctx.lineWidth = 2;
  ctx.strokeRect(4, 4, 472, 212);
  ctx.fillStyle = "#27272a";
  ctx.fillRect(5, 5, 470, 34);
  ctx.fillStyle = "#fafafa";
  ctx.font = "600 13px sans-serif";
  ctx.fillText(shot.title, 16, 26);
  ctx.fillStyle = "#f87171";
  ctx.font = "600 14px monospace";
  ctx.fillText(shot.code, 18, 76);
  ctx.fillStyle = "#d4d4d8";
  ctx.font = "12px monospace";
  ctx.fillText(shot.detail, 18, 110);
  ctx.fillText("Host: srv-rds-01.corp.example.test / Timestamp: UTC", 18, 138);
  ctx.fillStyle = "#3f3f46";
  ctx.fillRect(370, 168, 86, 28);
  ctx.fillStyle = "#fafafa";
  ctx.font = "12px sans-serif";
  ctx.fillText("OK", 404, 186);
  return canvas.toDataURL("image/png");
}

function useSampleShot(key) {
  const shot = SAMPLE_SHOTS[key];
  setScreenshot(syntheticDialogPng(shot), shot.name, shot.caption);
  if (!ui.ticket.value.trim()) setTicket(shot.ticket);
}

/* ---------- RMM output loop ---------- */

function attachRmmLoop(output, cmd) {
  state.rmmLoopOutput = output;
  setText(ui.rmmLoopSummary, "RMM output attached for re-triage: " + String(cmd || "RMM check").slice(0, 60));
  show(ui.rmmLoopBar, true);
}

function clearRmmLoop() {
  state.rmmLoopOutput = null;
  show(ui.rmmLoopBar, false);
}

/* ---------- Queue ---------- */

function renderQueue() {
  clear(ui.queueList);
  setText(ui.queueCount, String(state.queueItems.length));
  if (state.queueItems.length === 0) {
    ui.queueList.appendChild(
      el("li", { class: "list-empty", text: state.stagedOnly ? "No tickets from staged connectors yet. Set one up in Integrations, or show all." : "The queue is empty." })
    );
    return;
  }
  state.queueItems.forEach((item) => {
    const selected = state.activeQueueItem && state.activeQueueItem.id === item.id;
    const statusWord = queueStatus(item.status);
    const right = statusWord ? badge(statusWord) : badge(priority(item.priority), item.priority === "critical" ? "strong" : null);
    const host = item.device && item.device.hostname ? " · " + item.device.hostname : "";
    const row = el(
      "button",
      { type: "button", class: "list-row", "aria-pressed": selected ? "true" : "false", on: { click: () => selectQueueItem(item) } },
      el("span", { class: "list-row-top" }, el("span", { class: "list-row-meta", text: item.provider_name + " · " + item.external_ref + host }), right),
      el("span", { class: "list-row-title", text: item.title })
    );
    ui.queueList.appendChild(el("li", null, row));
  });
}

async function loadQueue() {
  const res = await get("/integrations/queue" + (state.stagedOnly ? "?staged_only=true" : ""));
  if (!res.ok || !Array.isArray(res.data)) return;
  state.queueItems = res.data;
  if (state.activeQueueItem) {
    const fresh = state.queueItems.find((i) => i.id === state.activeQueueItem.id);
    if (fresh) state.activeQueueItem = fresh;
  }
  renderQueue();
}

function selectQueueItem(item) {
  state.activeQueueItem = item;
  clearActiveSample();
  clearRmmLoop();
  setTicket(item.ticket_text || "");
  clearError();
  const host = item.device && item.device.hostname ? " · Host " + item.device.hostname : "";
  setText(ui.activeLabel, "Linked to " + item.external_ref + " (" + item.provider_name + ")" + host + ". Sample data.");
  show(ui.activeBar, true);
  emit("queue-selected", item);
  renderQueue();
  if (window.matchMedia("(max-width: 959px)").matches) ui.ticket.scrollIntoView({ block: "center" });
}

function unlinkQueueItem() {
  state.activeQueueItem = null;
  show(ui.activeBar, false);
  setText(ui.activeLabel, "");
  emit("queue-selected", null);
  renderQueue();
}

/* ---------- Submit ---------- */

function reasoningMode() {
  const checked = document.querySelector('input[name="reasoning-mode"]:checked');
  return checked ? checked.value : "standard";
}

export async function submitTriage() {
  if (busy) return;
  clearError();
  const ticket = ui.ticket.value;
  if (!ticket.trim()) {
    showError({ message: "Enter a ticket first, or pick a sample." });
    ui.ticket.focus();
    return;
  }
  if (ticket.length > MAX_CHARS) {
    showError({ message: "The ticket is over 4000 characters. Make it shorter." });
    return;
  }
  await ensureIndex();

  busy = true;
  ui.submit.disabled = true;
  ui.submit.setAttribute("aria-busy", "true");
  showState("loading");
  startTimer();
  const t0 = performance.now();

  const body = { ticket, reasoning_mode: reasoningMode() };
  if (state.screenshot) {
    body.screenshot_data_url = state.screenshot.dataUrl;
    if (state.screenshot.caption) body.screenshot_caption = state.screenshot.caption;
  }
  if (state.rmmLoopOutput) body.rmm_diagnostic_output = state.rmmLoopOutput;

  const res = await post("/triage", body);
  stopTimer();
  busy = false;
  ui.submit.disabled = false;
  ui.submit.removeAttribute("aria-busy");

  if (!res.ok || !res.data) {
    showState(state.lastResult ? "result" : "empty");
    showError(res.ok ? { ...res, message: "The model sent no usable answer. Try again." } : res);
    return;
  }

  const meta = triageMeta(res);
  meta.elapsedSeconds = ((performance.now() - t0) / 1000).toFixed(1);
  meta.vision = Boolean(state.screenshot);
  meta.rmmLoop = Boolean(state.rmmLoopOutput);
  state.lastTicket = ticket;
  document.querySelectorAll(".js-model-name").forEach((n) => setText(n, modelName(meta.metaModel)));
  showState("result");
  renderResult(ui.result, res.data, meta);
}

function clearAll() {
  unlinkQueueItem();
  clearActiveSample();
  clearScreenshot();
  clearRmmLoop();
  setTicket("");
  clearError();
  stopTimer();
  state.lastResult = null;
  resetResult(ui.result);
  showState("empty");
  ui.ticket.focus();
}

/* ---------- Init ---------- */

export function initTriage() {
  ui = {
    form: byId("triage-form"),
    ticket: byId("ticket-input"),
    charCount: byId("char-count"),
    submit: byId("submit-btn"),
    clearBtn: byId("clear-btn"),
    errorRegion: byId("error-region"),
    sampleList: byId("sample-list"),
    activeBar: byId("active-ticket-bar"),
    activeLabel: byId("active-ticket-label"),
    rmmLoopBar: byId("rmm-loop-bar"),
    rmmLoopSummary: byId("rmm-loop-summary"),
    shotInput: byId("screenshot-file-input"),
    dropZone: byId("drop-zone"),
    shotPreview: byId("screenshot-preview"),
    shotThumb: byId("screenshot-thumb"),
    shotName: byId("screenshot-name"),
    shotCaption: byId("screenshot-caption"),
    queueList: byId("pending-queue-list"),
    queueCount: byId("queue-count"),
    queueFilter: byId("queue-staged-filter-btn"),
    empty: byId("empty-state"),
    loading: byId("loading-state"),
    timer: byId("loading-timer"),
    result: byId("result-container")
  };

  renderSamples();
  updateCharCount();

  ui.form.addEventListener("submit", (e) => {
    e.preventDefault();
    submitTriage();
  });
  ui.ticket.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      submitTriage();
    }
  });
  ui.ticket.addEventListener("input", () => {
    clearActiveSample();
    updateCharCount();
  });
  ui.clearBtn.addEventListener("click", clearAll);

  byId("run-demo-btn").addEventListener("click", () => {
    pickSample("lockout");
    submitTriage();
  });

  ui.shotInput.addEventListener("change", () => readScreenshotFile(ui.shotInput.files && ui.shotInput.files[0]));
  ui.dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    ui.dropZone.dataset.drag = "true";
  });
  ui.dropZone.addEventListener("dragleave", () => delete ui.dropZone.dataset.drag);
  ui.dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    delete ui.dropZone.dataset.drag;
    readScreenshotFile(e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]);
  });
  byId("btn-sample-shot-rdp").addEventListener("click", () => useSampleShot("rdp"));
  byId("btn-sample-shot-vss").addEventListener("click", () => useSampleShot("vss"));
  byId("btn-remove-screenshot").addEventListener("click", clearScreenshot);
  byId("btn-clear-rmm-loop").addEventListener("click", clearRmmLoop);
  byId("unlink-ticket-btn").addEventListener("click", unlinkQueueItem);

  ui.queueFilter.addEventListener("click", () => {
    state.stagedOnly = !state.stagedOnly;
    ui.queueFilter.setAttribute("aria-pressed", state.stagedOnly ? "true" : "false");
    loadQueue();
  });
  byId("queue-refresh-btn").addEventListener("click", loadQueue);

  // Events from the result view.
  on("rmm-retriage", ({ output, command }) => {
    attachRmmLoop(output, command);
    submitTriage();
  });
  on("retriage", () => submitTriage());
  on("queue-changed", () => loadQueue());

  showState("empty");
}

export function onTriageShown() {
  loadQueue();
}
