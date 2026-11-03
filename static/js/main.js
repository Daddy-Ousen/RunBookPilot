// Boot: theme, toast, views, router, mobile menu.

import { byId } from "./dom.js";
import { initTheme } from "./theme.js";
import { initToast } from "./toast.js";
import { initRouter, onRoute } from "./router.js";
import { initRunbooks } from "./views/runbooks.js";
import { initTriage, onTriageShown } from "./views/triage.js";
import { initSafety, onSafetyShown } from "./views/safety.js";
import { initBenchmark, onBenchmarkShown } from "./views/benchmark.js";
import { initIntegrations, onIntegrationsShown } from "./views/integrations.js";

function initMenu() {
  const btn = byId("menu-btn");
  const nav = byId("app-nav");
  const setOpen = (open) => {
    nav.dataset.open = open ? "true" : "false";
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  };
  btn.addEventListener("click", () => {
    const open = nav.dataset.open !== "true";
    setOpen(open);
    if (open) {
      const current = nav.querySelector('[aria-current="page"]') || nav.querySelector("a");
      if (current) current.focus();
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && nav.dataset.open === "true") {
      setOpen(false);
      btn.focus();
    }
  });
  document.addEventListener("click", (e) => {
    if (nav.dataset.open === "true" && !nav.contains(e.target) && !btn.contains(e.target)) setOpen(false);
  });
  document.addEventListener("routechange", () => setOpen(false));
}

function initSkipLink() {
  const link = document.querySelector(".skip-link");
  link.addEventListener("click", (e) => {
    e.preventDefault();
    byId("main").focus();
  });
}

initTheme(byId("theme-toggle"));
initToast(byId("toast-region"));
initSkipLink();
initMenu();
initRunbooks();
initTriage();
initSafety();
initBenchmark();
initIntegrations();

onRoute("triage", onTriageShown);
onRoute("safety", onSafetyShown);
onRoute("benchmark", onBenchmarkShown);
onRoute("integrations", onIntegrationsShown);
initRouter();
