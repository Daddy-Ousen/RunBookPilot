// Raw API terms to UI text (docs/design-plan.md section 8).

export const RISK = {
  read_only: { word: "Read-only", long: "Read-only", variant: "ro" },
  needs_approval: { word: "Needs approval", long: "Changes the system. Needs approval.", variant: "na" }
};

export function risk(raw) {
  return RISK[raw === "read_only" ? "read_only" : "needs_approval"];
}

// Plain words for raw risk labels inside a sentence from the API.
export function plainRisk(text) {
  return String(text || "")
    .replace(/read_only/g, "read-only")
    .replace(/needs_approval/g, "needs approval");
}

export function confidence(raw) {
  const level = ["low", "medium", "high"].includes(raw) ? raw : "low";
  return { level, text: level.charAt(0).toUpperCase() + level.slice(1) + " confidence" };
}

export function capital(raw) {
  const s = String(raw || "");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function priority(raw) {
  return capital(raw || "medium");
}

export function queueStatus(raw) {
  if (raw === "triaged") return "Triaged";
  if (raw === "escalated") return "Escalated";
  return "Pending";
}

export function connectorStatus(raw) {
  if (raw === "staged") return "Ready (staged)";
  if (raw === "paused") return "Paused";
  return "Not set up";
}

export function modelName(raw) {
  // "muse-spark-1.3" -> "Muse Spark 1.3"
  if (!raw) return "Muse Spark 1.3";
  return String(raw)
    .split("-")
    .map((part) => (/^\d/.test(part) ? part : capital(part)))
    .join(" ");
}

export function countsLine(roCount, naCount) {
  const parts = [];
  if (roCount) parts.push(roCount + " read-only");
  if (naCount) parts.push(naCount + (naCount === 1 ? " changes" : " change") + " the system");
  return parts.join(", ") || "No commands";
}

export const NOT_RUN = "Not run by RunbookPilot.";
export const NEVER_RUNS = "RunbookPilot never runs commands. Copy and run them yourself.";

// HTTP error to UI text: { title: what failed, next: what to do }.
// retryAfter in seconds when known. status 0 = network, "timeout" = no answer in time.
export function errorParts(status, retryAfter) {
  switch (status) {
    case 429:
      return {
        title: "The model is busy.",
        next: retryAfter ? "Wait " + retryAfter + " s, then try again." : "Wait a moment, then try again."
      };
    case 504:
    case "timeout":
      return { title: "The model took too long.", next: "Try again, or use Standard mode." };
    case 502:
    case 500:
      return { title: "The model sent no usable answer.", next: "Try again. If it fails again, use Standard mode." };
    case 503:
      return { title: "The service is not ready.", next: "Wait a moment, then try again." };
    case 422:
    case 400:
    case 413:
      return { title: "The ticket could not be read.", next: "Check the text and try again." };
    case 0:
      return { title: "No connection to RunbookPilot.", next: "Check the server, then try again." };
    default:
      return { title: "Something went wrong (HTTP " + status + ").", next: "Try again." };
  }
}

export function errorText(status, retryAfter) {
  const parts = errorParts(status, retryAfter);
  return parts.title + " " + parts.next;
}

// Verdict state word for a triage result.
export function verdict(data, naCount) {
  if (data.escalate) return { word: "Escalate to Tier 3", variant: "esc" };
  if (naCount > 0) return { word: "Needs approval steps", variant: "na" };
  return { word: "Covered by runbooks", variant: "ro" };
}

// ISO time to a short age: "40 min", "3 h", "2 d".
export function age(iso) {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "";
  const mins = Math.max(0, Math.round((Date.now() - t) / 60000));
  if (mins < 60) return mins + " min";
  const hours = Math.round(mins / 60);
  if (hours < 48) return hours + " h";
  return Math.round(hours / 24) + " d";
}
