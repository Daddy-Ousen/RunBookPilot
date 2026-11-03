// PowerShell colors for command blocks. Splits the text into spans and sets
// each one with textContent only. The command string itself is not changed,
// so Copy still copies cmd.command as it came from the API.

import { el, clear } from "./dom.js";

const TOKEN = /'[^']*'?|"[^"]*"?|\s+|[|;(){}@=,[\]]|[^\s'"|;(){}@=,[\]]+/g;

function kind(tok) {
  if (tok[0] === "'" || tok[0] === '"') return "str";
  if (/^[A-Za-z]+-[A-Za-z][\w]*$/.test(tok)) return "cmdlet";
  if (/^-[A-Za-z]/.test(tok)) return "param";
  if (/^\$[\w:]+$/.test(tok)) return "var";
  if (/^[|;]$/.test(tok)) return "op";
  return null;
}

export function highlightPs(node, text) {
  clear(node);
  const source = text == null ? "" : String(text);
  for (const tok of source.match(TOKEN) || []) {
    const k = kind(tok);
    node.appendChild(k ? el("span", { class: "ps-" + k, text: tok }) : document.createTextNode(tok));
  }
  return node;
}
