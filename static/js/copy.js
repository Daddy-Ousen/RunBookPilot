// Raw API terms to UI text (docs/design-plan.md section 8).

export const RISK = {
  read_only: { word: "Read-only", long: "Read-only", variant: "ro" },
  needs_approval: { word: "Needs approval", long: "Changes the system. Needs approval.", variant: "na" }
};

export function risk(raw) {
  return RISK[raw === "read_only" ? "read_only" : "needs_approval"];
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
  return null;
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

// HTTP error to UI text. retryAfter in seconds when known.
export function errorText(status, retryAfter) {
  switch (status) {
    case 429:
      return retryAfter ? "The model is busy. Wait " + retryAfter + " s, then try again." : "The model is busy. Wait a moment, then try again.";
    case 504:
      return "The model took too long. Try again, or use Standard mode.";
    case 502:
    case 500:
      return "The model sent no usable answer. Try again.";
    case 503:
      return "The service is not ready. Wait a moment, then try again.";
    case 422:
    case 400:
    case 413:
      return "The ticket could not be read. Check the text and try again.";
    case 0:
      return "No connection to RunbookPilot. Check the server, then try again.";
    default:
      return "Something went wrong (HTTP " + status + "). Try again.";
  }
}
