// Hash router. #triage is the default; #eval is an old alias for #benchmark.

const ROUTES = {
  triage: "Triage",
  runbooks: "Runbooks",
  safety: "Safety lab",
  benchmark: "Benchmark",
  integrations: "Integrations"
};
const ALIASES = { eval: "benchmark" };

const handlers = new Map();
let current = null;

export function onRoute(name, fn) {
  handlers.set(name, fn);
}

export function currentRoute() {
  return current;
}

function parse() {
  const raw = window.location.hash.replace(/^#/, "").toLowerCase();
  if (ALIASES[raw]) return { name: ALIASES[raw], alias: true };
  if (ROUTES[raw]) return { name: raw, alias: false };
  // Unknown hash (for example the skip link's #main): keep the current view.
  return { name: raw && current ? current : "triage", alias: false };
}

function apply(focus) {
  const { name, alias } = parse();
  if (alias) history.replaceState(null, "", "#" + name);

  document.querySelectorAll("[data-view]").forEach((section) => {
    section.hidden = section.getAttribute("data-view") !== name;
  });
  document.querySelectorAll("[data-route]").forEach((link) => {
    if (link.getAttribute("data-route") === name) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  document.title = ROUTES[name] + " · RunbookPilot";
  const viewLabel = document.getElementById("topbar-view");
  if (viewLabel) viewLabel.textContent = "· " + ROUTES[name];

  const changed = current !== name;
  current = name;
  if (focus && changed) {
    const heading = document.querySelector('[data-view="' + name + '"] h1');
    if (heading) heading.focus({ preventScroll: false });
    window.scrollTo(0, 0);
  }
  const fn = handlers.get(name);
  if (fn) fn();
  document.dispatchEvent(new CustomEvent("routechange", { detail: { name } }));
}

export function initRouter() {
  window.addEventListener("hashchange", () => apply(true));
  apply(false);
}
