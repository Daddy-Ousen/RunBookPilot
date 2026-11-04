// Model picker: shows the model in use and the models that are not available in the demo.
// Only Muse Spark Open runs. The other choices explain themselves and change nothing.

import { el, setText } from "./dom.js";
import { toast } from "./toast.js";

export const MODELS = [
  { id: "muse-spark-open", name: "Muse Spark Open", available: true },
  { id: "muse-spark-1.3", name: "Muse Spark 1.3", available: false },
  { id: "muse-wonder", name: "Muse Wonder", available: false },
];

const UNAVAILABLE = "Not available in demo";
let uid = 0;

function buildPicker(mount) {
  const n = ++uid;
  const listId = "model-list-" + n;
  const selected = MODELS[0];
  const caret = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  caret.setAttribute("width", "16");
  caret.setAttribute("height", "16");
  caret.setAttribute("viewBox", "0 0 24 24");
  caret.setAttribute("fill", "none");
  caret.setAttribute("stroke", "currentColor");
  caret.setAttribute("stroke-width", "2.25");
  caret.setAttribute("stroke-linecap", "round");
  caret.setAttribute("stroke-linejoin", "round");
  caret.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M6 9l6 6 6-6");
  caret.appendChild(path);

  const button = el(
    "button",
    { type: "button", class: "model-picker-btn", "aria-haspopup": "listbox", "aria-expanded": "false", "aria-controls": listId },
    el("span", { class: "model-picker-label", text: "Model:" }),
    el("span", { class: "model-picker-current", text: selected.name }),
    caret,
  );

  const options = MODELS.map((m) =>
    el(
      "li",
      {
        role: "option",
        class: "model-option",
        id: listId + "-" + m.id,
        tabindex: "-1",
        "aria-selected": m.available ? "true" : "false",
        "aria-disabled": m.available ? null : "true",
        dataset: { model: m.id },
      },
      el("span", { class: "model-option-name", text: m.name }),
      el("span", { class: "model-option-note", text: m.available ? "In use" : UNAVAILABLE }),
    ),
  );
  const list = el("ul", { role: "listbox", class: "model-picker-menu", id: listId, "aria-label": "Model", hidden: true }, options);
  const wrap = el("div", { class: "model-picker", dataset: { placement: mount.dataset.placement || "down" } }, button, list);
  mount.appendChild(wrap);

  const setOpen = (open, focusIndex) => {
    list.hidden = !open;
    button.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) options[focusIndex == null ? 0 : focusIndex].focus();
  };
  const choose = (i) => {
    const m = MODELS[i];
    if (!m.available) {
      toast(m.name + " is not available in the demo. Muse Spark Open is in use.");
      return;
    }
    setText(button.querySelector(".model-picker-current"), m.name);
    setOpen(false);
    button.focus();
  };

  button.addEventListener("click", () => setOpen(list.hidden));
  button.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      setOpen(true, e.key === "ArrowUp" ? options.length - 1 : 0);
    }
  });
  options.forEach((opt, i) => {
    opt.addEventListener("click", () => choose(i));
    opt.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        options[(i + 1) % options.length].focus();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        options[(i - 1 + options.length) % options.length].focus();
      } else if (e.key === "Home") {
        e.preventDefault();
        options[0].focus();
      } else if (e.key === "End") {
        e.preventDefault();
        options[options.length - 1].focus();
      } else if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        choose(i);
      } else if (e.key === "Escape" || e.key === "Tab") {
        const wasEscape = e.key === "Escape";
        setOpen(false);
        if (wasEscape) button.focus();
      }
    });
  });
  document.addEventListener("click", (e) => {
    if (!list.hidden && !wrap.contains(e.target)) setOpen(false);
  });
}

export function initModelPickers() {
  document.querySelectorAll(".js-model-picker").forEach(buildPicker);
}
