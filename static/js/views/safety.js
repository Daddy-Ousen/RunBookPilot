// Safety lab: check how the safety rules label a command. Nothing is run.

import { el, byId, clear, setText } from "../dom.js";
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

async function inspect(command) {
  ui.button.disabled = true;
  const res = await post("/safety/inspect", { command });
  ui.button.disabled = false;
  checkedOnce = true;
  clear(ui.stages);
  if (!res.ok) {
    ui.badge.className = "badge";
    setText(ui.badge, "Not checked");
    setText(ui.reason, res.message + (res.detail ? " " + res.detail : ""));
    return;
  }
  const r = risk(res.data.risk);
  ui.badge.className = "badge badge-" + r.variant;
  setText(ui.badge, r.long);
  setText(ui.reason, res.data.reason || "");
  const stages = Array.isArray(res.data.stages) && res.data.stages.length ? res.data.stages : ["(empty command)"];
  stages.forEach((s) => ui.stages.appendChild(el("li", { class: "mono wrap-anywhere", text: s })));
}

export function initSafety() {
  ui = {
    form: byId("safety-inspect-form"),
    input: byId("safety-cmd-input"),
    button: byId("btn-safety-inspect"),
    badge: byId("safety-verdict-badge"),
    reason: byId("safety-verdict-reason"),
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
