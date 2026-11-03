// DOM helpers. Dynamic text goes in with textContent only, never as HTML strings.

const SVG_NS = "http://www.w3.org/2000/svg";

// el("button", { class: "btn", type: "button", text: "Copy", on: { click } }, child, ...)
// Props: class, text, dataset, on, attrs (raw attributes); any other key is set
// as an attribute, except boolean true/false which toggles the attribute.
export function el(tag, props, ...children) {
  const node = document.createElement(tag);
  if (props) {
    for (const [key, value] of Object.entries(props)) {
      if (value === undefined || value === null) continue;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = String(value);
      else if (key === "dataset") Object.assign(node.dataset, value);
      else if (key === "on") {
        for (const [evt, fn] of Object.entries(value)) node.addEventListener(evt, fn);
      } else if (key === "value" || key === "checked" || key === "disabled" || key === "hidden") {
        node[key] = value;
      } else if (value === true) node.setAttribute(key, "");
      else if (value === false) continue;
      else node.setAttribute(key, String(value));
    }
  }
  append(node, children);
  return node;
}

export function append(node, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    node.appendChild(typeof child === "string" || typeof child === "number" ? document.createTextNode(String(child)) : child);
  }
  return node;
}

export function clear(node) {
  node.textContent = "";
  return node;
}

export function setText(node, text) {
  node.textContent = text == null ? "" : String(text);
  return node;
}

export function show(node, visible = true) {
  node.hidden = !visible;
  return node;
}

export function byId(id) {
  return document.getElementById(id);
}

export function icon(paths, size = 16) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("width", String(size));
  svg.setAttribute("height", String(size));
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.75");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  for (const d of paths) {
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", d);
    svg.appendChild(path);
  }
  return svg;
}

export const ICONS = {
  copy: ["M9 9h11a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2v-9a2 2 0 0 1 2-2z", "M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"],
  check: ["M20 6L9 17l-5-5"],
  warn: ["M12 3l10 18H2z", "M12 10v4", "M12 17.5v.01"],
  eye: ["M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z", "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"],
  hand: ["M7 11V6a2 2 0 0 1 4 0v5", "M11 10V4a2 2 0 0 1 4 0v6", "M15 10V6a2 2 0 0 1 4 0v7a8 8 0 0 1-8 8h-1a6 6 0 0 1-5-3l-2-4a2 2 0 0 1 3-2l1 1"]
};

// Badge with optional variant: "ro" | "na" | "esc" | "staged" | "strong"
export function badge(text, variant) {
  return el("span", { class: "badge" + (variant ? " badge-" + variant : ""), text });
}

// Notice block: kind "warning" | "danger" | "ok" | "staged" | undefined
export function notice(kind, title, body, ...extra) {
  return el(
    "div",
    { class: "notice" + (kind ? " notice-" + kind : ""), role: kind === "danger" ? "alert" : null },
    title ? el("span", { class: "notice-title", text: title }) : null,
    body ? el("span", { text: body }) : null,
    ...extra
  );
}
