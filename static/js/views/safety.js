// Safety lab: check how the safety rules label a command. Nothing is run.

import { el, byId, clear, setText, show, icon, ICONS, notice } from "../dom.js";
import { post } from "../api.js";
import { risk } from "../copy.js";

const PRESETS = [
  { label: "Get-ADUser", note: "Safe read", cmd: "Get-ADUser -Identity user01 -Properties LockedOut, BadPwdCount, LastBadPasswordAttempt" },
  { label: "Semicolon chain", note: "Hides a change after a read", cmd: "Get-Service Spooler; Stop-Service Spooler -Force" },
  { label: "-EncodedCommand", note: "Hidden script", cmd: "powershell.exe -NoProfile -EncodedCommand SQBFAFgA" },
  { label: "$() subexpression", note: "Change inside a read", cmd: "Write-Output $(Remove-Item C:\\Temp\\cache -Recurse)" },
  { label: "Format-Volume pipe", note: "Change at the end of a pipe", cmd: "Get-Partition -DriveLetter D | Format-Volume -FileSystem NTFS" },
  { label: "Get-WinEvent 4740", note: "Safe read", cmd: "Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4740} -MaxEvents 10" }
];

let ui = {};
let checkedOnce = false;
let lastCommand = "";

function showError(message, detail) {
  show(ui.empty, false);
  show(ui.block, false);
  show(ui.tech, false);
  clear(ui.error);
  ui.error.appendChild(
    notice(
      "danger",
      "The check did not finish.",
      message,
      el("div", { class: "btn-row notice-actions" }, el("button", { type: "button", class: "btn btn-secondary btn-sm", text: "Try again", on: { click: () => inspect(lastCommand) } })),
      detail ? el("details", { class: "disclosure" }, el("summary", { text: "Technical details" }), el("p", { class: "mono t-sm wrap-anywhere", text: detail })) : null
    )
  );
  show(ui.error, true);
}

async function inspect(command) {
  const text = String(command || "").trim();
  if (!text) {
    showError("Type a PowerShell command first.", "");
    return;
  }
  lastCommand = command;
  ui.button.disabled = true;
  ui.button.setAttribute("aria-busy", "true");
  const res = await post("/safety/inspect", { command });
  ui.button.disabled = false;
  ui.button.removeAttribute("aria-busy");
  checkedOnce = true;
  if (!res.ok || !res.data) {
    showError(res.message || "Try again.", res.detail);
    return;
  }
  const d = res.data;
  const r = risk(d.risk);
  const isRo = d.risk === "read_only";

  show(ui.empty, false);
  show(ui.error, false);
  ui.block.className = "cmd cmd-" + r.variant;
  ui.block.setAttribute("aria-label", isRo ? "Read-only command" : "Command that changes the system. Needs approval.");
  clear(ui.tabIcon).appendChild(icon(isRo ? ICONS.eye : ICONS.hand, 14));
  setText(ui.tabWord, r.word);
  setText(ui.verdict, r.long);
  setText(ui.reason, d.reason || (isRo ? "No rule found a change in this command." : "A rule found a change, or could not rule one out."));
  setText(ui.checked, command);
  show(ui.block, true);

  // Raw terms stay in the collapsed Technical details.
  setText(ui.rawRisk, String(d.risk));
  setText(ui.rawExecuted, String(d.executed_on_host));
  clear(ui.stages);
  const stages = Array.isArray(d.stages) ? d.stages : [];
  if (stages.length) stages.forEach((s) => ui.stages.appendChild(el("li", { class: "mono wrap-anywhere", text: s })));
  else ui.stages.appendChild(el("li", { class: "text-3", text: "None." }));
  show(ui.tech, true);
}

export function initSafety() {
  ui = {
    form: byId("safety-inspect-form"),
    input: byId("safety-cmd-input"),
    button: byId("btn-safety-inspect"),
    empty: byId("safety-empty"),
    block: byId("safety-block"),
    tabIcon: byId("safety-tab-icon"),
    tabWord: byId("safety-tab-word"),
    verdict: byId("safety-verdict-badge"),
    reason: byId("safety-verdict-reason"),
    checked: byId("safety-checked-cmd"),
    error: byId("safety-error"),
    tech: byId("safety-tech"),
    rawRisk: byId("safety-raw-risk"),
    rawExecuted: byId("safety-raw-executed"),
    stages: byId("safety-stages-list"),
    presets: byId("safety-preset-list")
  };
  PRESETS.forEach((p) => {
    ui.presets.appendChild(
      el(
        "li",
        null,
        el(
          "button",
          {
            type: "button",
            class: "list-row",
            on: {
              click: () => {
                ui.input.value = p.cmd;
                inspect(p.cmd);
              }
            }
          },
          el("span", { class: "list-row-top" }, el("span", { class: "list-row-title", text: p.label }), el("span", { class: "list-row-meta", text: p.note })),
          el("span", { class: "list-row-meta mono", text: p.cmd })
        )
      )
    );
  });
  ui.form.addEventListener("submit", (e) => {
    e.preventDefault();
    inspect(ui.input.value);
  });
}

export function onSafetyShown() {
  if (!checkedOnce) inspect(ui.input.value);
}
