// Theme: follow the system by default. The toggle saves an explicit choice.

import { load, save } from "./store.js";

const KEY = "rbp_theme";
const root = document.documentElement;
const BAR_COLOR = { light: "#f5f6f8", dark: "#0e1014" };
const media = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

function effective() {
  const set = root.getAttribute("data-theme");
  if (set === "light" || set === "dark") return set;
  return media && media.matches ? "dark" : "light";
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

// Browser bar color: an explicit choice wins over the system setting.
function syncBarColor() {
  const set = root.getAttribute("data-theme");
  ["light", "dark"].forEach((name) => {
    const meta = document.getElementById("theme-color-" + name);
    if (meta) meta.setAttribute("content", BAR_COLOR[set === "light" || set === "dark" ? set : name]);
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
  if (media && media.addEventListener) media.addEventListener("change", () => sync(button));
}
