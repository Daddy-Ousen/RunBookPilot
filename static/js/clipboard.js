// Copy text, with a fallback for non-secure contexts.
// copyButton() makes a button that shows "Copied" for 2 s.

import { el, icon, ICONS, clear, append } from "./dom.js";

export async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (_e) {
      /* Permission denied: try the older path below */
    }
  }
  try {
    const helper = el("textarea", { class: "sr-only", "aria-hidden": "true" });
    helper.value = text;
    document.body.appendChild(helper);
    const previous = document.activeElement;
    helper.focus();
    helper.select();
    const ok = document.execCommand("copy");
    helper.remove();
    if (previous && previous.focus) previous.focus();
    return ok;
  } catch (_e) {
    return false;
  }
}

function paint(btn, state, label) {
  clear(btn);
  if (state === "copied") append(btn, [icon(ICONS.check, 14), el("span", { text: "Copied" })]);
  else if (state === "failed") append(btn, [el("span", { text: "Select and copy" })]);
  else append(btn, [icon(ICONS.copy, 14), el("span", { text: label })]);
}

// getText: () => string. onFail: optional, called so the caller can select the text.
// onDone(ok): optional, called after each copy. liveText: what the live region says.
export function copyButton(getText, { label = "Copy", ariaLabel, onFail, onDone, liveRegion, liveText = "Copied" } = {}) {
  const btn = el("button", { type: "button", class: "btn btn-secondary btn-sm", "aria-label": ariaLabel || null });
  paint(btn, "idle", label);
  btn.addEventListener("click", async () => {
    const ok = await copyText(getText());
    paint(btn, ok ? "copied" : "failed", label);
    if (liveRegion) liveRegion.textContent = ok ? liveText : "Copy failed. Select the text and copy it.";
    if (!ok && onFail) onFail();
    if (onDone) onDone(ok);
    window.setTimeout(() => paint(btn, "idle", label), 2000);
  });
  return btn;
}
