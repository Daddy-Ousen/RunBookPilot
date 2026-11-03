// Small, safe Markdown renderer for runbooks. It builds DOM nodes with
// createElement and textContent only. No library, no HTML strings, no links.
// Supported: front matter, headings, paragraphs, lists, quotes, code fences,
// `inline code` and **bold**. Anything else shows as plain text.

import { el } from "./dom.js";

// "---\nkey: value\n---" at the top of a file. Returns { meta, body }.
export function parseFrontMatter(text) {
  const src = String(text || "").replace(/\r\n?/g, "\n");
  const meta = {};
  const m = src.match(/^---\n([\s\S]*?)\n---\n?/);
  if (!m) return { meta, body: src };
  m[1].split("\n").forEach((line) => {
    const kv = line.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (!kv) return;
    const value = kv[2].trim();
    if (value.startsWith("[") && value.endsWith("]")) {
      meta[kv[1]] = value
        .slice(1, -1)
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
    } else {
      meta[kv[1]] = value;
    }
  });
  return { meta, body: src.slice(m[0].length) };
}

const INLINE = /(`+)([^`]+?)\1|\*\*([^*]+?)\*\*/g;

// Inline nodes for one line of text.
function inline(text) {
  const nodes = [];
  let last = 0;
  INLINE.lastIndex = 0;
  let m;
  while ((m = INLINE.exec(text)) !== null) {
    if (m.index > last) nodes.push(document.createTextNode(text.slice(last, m.index)));
    if (m[2] !== undefined) nodes.push(el("code", { class: "md-code", text: m[2].trim() }));
    else nodes.push(el("strong", { text: m[3] }));
    last = m.index + m[0].length;
  }
  if (last < text.length) nodes.push(document.createTextNode(text.slice(last)));
  return nodes;
}

// A list item that holds one code span and nothing else is a command line.
function listItem(text) {
  const only = text.match(/^`([^`]+)`$/);
  if (only) return el("li", { class: "md-cmd" }, el("code", { class: "md-code", text: only[1] }));
  return el("li", null, ...inline(text));
}

// Markdown text to a <div class="md">. headingOffset 1 turns "##" into h3.
export function renderMarkdown(markdown, { headingOffset = 1 } = {}) {
  const root = el("div", { class: "md" });
  const lines = String(markdown || "").replace(/\r\n?/g, "\n").split("\n");
  let para = [];
  let list = null; // { node, ordered }
  let fence = null; // array of code lines

  const flushPara = () => {
    if (para.length) root.appendChild(el("p", null, ...inline(para.join(" "))));
    para = [];
  };
  const flushList = () => {
    list = null;
  };

  lines.forEach((raw) => {
    if (fence !== null) {
      if (/^\s*```/.test(raw)) {
        root.appendChild(el("pre", { class: "md-pre" }, el("code", { text: fence.join("\n") })));
        fence = null;
      } else {
        fence.push(raw);
      }
      return;
    }
    if (/^\s*```/.test(raw)) {
      flushPara();
      flushList();
      fence = [];
      return;
    }
    const line = raw.replace(/\s+$/, "");
    if (!line.trim()) {
      flushPara();
      flushList();
      return;
    }
    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      flushPara();
      flushList();
      const level = Math.min(6, heading[1].length + headingOffset);
      root.appendChild(el("h" + level, { class: "md-h", text: heading[2].replace(/[`*]/g, "") }));
      return;
    }
    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)$/);
    if (bullet || numbered) {
      flushPara();
      const ordered = Boolean(numbered);
      if (!list || list.ordered !== ordered) {
        list = { node: el(ordered ? "ol" : "ul", { class: "md-list" }), ordered };
        root.appendChild(list.node);
      }
      list.node.appendChild(listItem((bullet || numbered)[1].trim()));
      return;
    }
    const quote = line.match(/^>\s?(.*)$/);
    if (quote) {
      flushPara();
      flushList();
      root.appendChild(el("blockquote", { class: "md-quote" }, ...inline(quote[1])));
      return;
    }
    // A text line after a list item with deeper indent continues that item.
    if (list && /^\s{2,}\S/.test(raw) && list.node.lastChild) {
      list.node.lastChild.appendChild(document.createTextNode(" "));
      inline(line.trim()).forEach((n) => list.node.lastChild.appendChild(n));
      return;
    }
    flushList();
    para.push(line.trim());
  });
  if (fence !== null) root.appendChild(el("pre", { class: "md-pre" }, el("code", { text: fence.join("\n") })));
  flushPara();
  return root;
}

// First list item or sentence under "Symptoms", as plain text for a list row.
export function shortLine(markdown, max = 140) {
  const { body } = parseFrontMatter(markdown);
  const lines = body.split("\n");
  let inSymptoms = false;
  let pick = "";
  for (const line of lines) {
    if (/^##\s/.test(line)) inSymptoms = /symptom/i.test(line);
    else if (inSymptoms && /^\s*[-*]\s+/.test(line)) {
      pick = line.replace(/^\s*[-*]\s+/, "");
      break;
    }
  }
  if (!pick) pick = lines.find((l) => l.trim() && !/^#/.test(l)) || "";
  pick = pick.replace(/[`*]/g, "").trim();
  if (pick.length <= max) return pick;
  const cut = pick.slice(0, max);
  return cut.slice(0, Math.max(cut.lastIndexOf(" "), 40)).replace(/[,;:.\s]+$/, "") + "…";
}
