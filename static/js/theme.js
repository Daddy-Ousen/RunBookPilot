// Theme: light by default (owner choice). The toggle saves an explicit choice.

import { load, save } from "./store.js";

const KEY = "rbp_theme";
const root = document.documentElement;
const BAR_COLOR = { light: "#f4f2ff", dark: "#120f24" };

function effective() {
  return root.getAttribute("data-theme") === "dark" ? "dark" : "light";
}

function sync(button) {
  const current = effective();
  syncBarColor();
  const next = current === "dark" ? "light" : "dark";
  button.setAttribute("aria-label", "Switch to " + next + " theme");
  button.title = "Switch to " + next + " theme";
  // SVG elements have no hidden property; set the attribute.
  button.querySelector(".icon-moon").toggleAttribute("hidden", current === "dark");
  button.querySelector(".icon-sun").toggleAttribute("hidden", current !== "dark");
}

// Browser bar color follows the page theme, not the system setting.
function syncBarColor() {
  const color = BAR_COLOR[effective()];
  ["light", "dark"].forEach((name) => {
    const meta = document.getElementById("theme-color-" + name);
    if (meta) meta.setAttribute("content", color);
  });
}

export function initTheme(button) {
  const saved = load(KEY);
  if (saved === "light" || saved === "dark") root.setAttribute("data-theme", saved);
  sync(button);
  button.addEventListener("click", () => {
    const next = effective() === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    save(KEY, next);
    sync(button);
  });
}
