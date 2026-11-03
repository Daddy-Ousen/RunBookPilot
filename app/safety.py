"""Deterministic PowerShell command risk classifier for RunbookPilot.

Never trusts LLM-assigned risk labels. Every command is classified deterministically
as 'read_only' or 'needs_approval' (default-deny).
"""

from __future__ import annotations

import re

from app.schema import CommandItem, CommandRisk, TriageResult

_CMDLET_RE = re.compile(r"^([A-Za-z]+)-([A-Za-z][A-Za-z0-9]*)$")

_ALLOWED_VERBS = frozenset({"get", "test", "select", "measure", "format"})
_ALLOWED_STANDALONE = frozenset({"ipconfig", "nslookup", "ping", "hostname"})

_BLOCKED_VERBS = frozenset(
    {
        "remove",
        "set",
        "stop",
        "restart",
        "disable",
        "clear",
        "invoke",
        "start",
        "new",
        "enable",
        "unlock",
        "reset",
        "repair",
    }
)

_BLOCKED_CMDLETS = frozenset(
    {
        "format-volume",
        "format-disk",
        "format-partition",
        "invoke-expression",
        "iex",
    }
)

_ENCODED_FLAG_RE = re.compile(
    r"^[-/](?:e|ec|enc|encoded|encodedcommand)(?::|=|$)",
    re.IGNORECASE,
)

_BLOCKED_PARAM_FLAGS = frozenset({"-repair", "-outfile"})

_SAFE_IPCONFIG_ARGS = frozenset({"/all", "/displaydns", "/?", "-all", "-displaydns"})

# Forbidden unquoted shell metacharacters:
# ; (statement chaining), & (&& chaining, call operator, background operator),
# > / < (redirection), ( / ) (parenthetical sub-command), { / } (scriptblock), # (comment)
_FORBIDDEN_UNQUOTED_CHARS = frozenset({";", "&", ">", "<", "(", ")", "{", "}", "#"})


def _split_pipeline_and_tokenize(command: str) -> list[list[str]] | None:
    """Parse a single-line PowerShell command into pipeline stages of tokens.

    Returns None if quotes are unbalanced or forbidden metacharacters/operators appear.
    """
    if not command or "\n" in command or "\r" in command or "\x00" in command:
        return None

    # Block backtick escape/obfuscation and $() subexpressions everywhere (including double quotes).
    if "`" in command or "$(" in command:
        return None

    if "frombase64string" in command.lower():
        return None

    stages: list[list[str]] = []
    current_stage: list[str] = []
    current_token: list[str] = []

    in_single = False
    in_double = False
    idx = 0
    length = len(command)

    while idx < length:
        ch = command[idx]

        if in_single:
            if ch == "'":
                # PowerShell escapes a literal single quote inside '...' as ''
                if idx + 1 < length and command[idx + 1] == "'":
                    current_token.append("'")
                    idx += 2
                    continue
                in_single = False
            else:
                current_token.append(ch)
            idx += 1
            continue

        if in_double:
            if ch == '"':
                if idx + 1 < length and command[idx + 1] == '"':
                    current_token.append('"')
                    idx += 2
                    continue
                in_double = False
            else:
                current_token.append(ch)
            idx += 1
            continue

        # Unquoted context
        if ch == "'":
            in_single = True
            idx += 1
            continue

        if ch == '"':
            in_double = True
            idx += 1
            continue

        if ch in _FORBIDDEN_UNQUOTED_CHARS:
            return None

        if ch == "|":
            # Reject '||' logical chaining or empty pipeline stages
            if idx + 1 < length and command[idx + 1] == "|":
                return None
            if current_token:
                current_stage.append("".join(current_token))
                current_token = []
            if not current_stage:
                return None
            stages.append(current_stage)
            current_stage = []
            idx += 1
            continue

        if ch.isspace():
            if current_token:
                current_stage.append("".join(current_token))
                current_token = []
            idx += 1
            continue

        current_token.append(ch)
        idx += 1

    if in_single or in_double:
        return None

    if current_token:
        current_stage.append("".join(current_token))

    if not current_stage:
        return None

    stages.append(current_stage)
    return stages


def _is_stage_read_only(tokens: list[str]) -> bool:
    """Return True only if a single pipeline stage is strictly read-only."""
    if not tokens:
        return False

    cmd = tokens[0]
    cmd_lower = cmd.lower()
    args = tokens[1:]

    # Reject variable assignments, script paths, drive paths, or explicit blocked commands
    if cmd_lower in _BLOCKED_CMDLETS:
        return False
    if any(sep in cmd for sep in ("\\", "/", ":", "$", ".")):
        return False

    # Inspect arguments for encoded command switches or mutating flags
    for arg in args:
        arg_lower = arg.lower()
        if _ENCODED_FLAG_RE.match(arg_lower):
            return False
        flag_name = arg_lower.split(":", 1)[0]
        if flag_name in _BLOCKED_PARAM_FLAGS:
            return False

    # Check standalone diagnostic utility allowlist
    if cmd_lower in _ALLOWED_STANDALONE:
        if cmd_lower == "ipconfig":
            return all(arg.lower() in _SAFE_IPCONFIG_ARGS for arg in args)
        if cmd_lower == "hostname":
            return len(args) == 0
        return True

    # Check PowerShell Verb-Noun cmdlet allowlist
    match = _CMDLET_RE.match(cmd)
    if not match:
        return False

    verb = match.group(1).lower()
    if verb in _BLOCKED_VERBS:
        return False

    return verb in _ALLOWED_VERBS


def classify_command(command: str) -> CommandRisk:
    """Deterministically classify a PowerShell command as 'read_only' or 'needs_approval'."""
    stripped = command.strip()
    stages = _split_pipeline_and_tokenize(stripped)
    if not stages:
        return "needs_approval"

    for stage in stages:
        if not _is_stage_read_only(stage):
            return "needs_approval"

    return "read_only"


def apply_safety_overrides(result: TriageResult) -> TriageResult:
    """Return a copy of TriageResult with every command's risk overwritten deterministically."""
    updated_commands = [
        CommandItem(
            command=item.command,
            purpose=item.purpose,
            risk=classify_command(item.command),
        )
        for item in result.commands
    ]
    return result.model_copy(update={"commands": updated_commands})
