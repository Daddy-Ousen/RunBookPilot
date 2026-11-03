// Toast: bottom right, 4 s, one at a time is enough for this app.

import { el } from "./dom.js";

let region = null;

export function initToast(node) {
  region = node;
}

export function toast(message, ms = 4000) {
  if (!region) return;
  const node = el("div", { class: "toast", text: message });
  region.appendChild(node);
  while (region.children.length > 3) region.firstChild.remove();
  window.setTimeout(() => node.remove(), ms);
}
