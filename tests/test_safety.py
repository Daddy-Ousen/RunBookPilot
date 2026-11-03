"""Tests for deterministic PowerShell command risk classification in app/safety.py."""

from __future__ import annotations

import re

import pytest

from app.retrieval import RunbookIndex
from app.safety import apply_safety_overrides, classify_command
from app.schema import CommandItem, TriageResult


@pytest.mark.parametrize(
    "command",
    [
        "Get-Service -Name Spooler",
        "Get-ADUser -Identity user01 -Properties LockedOut, BadPwdCount",
        "Test-NetConnection -ComputerName srv-rds-01.corp.example.test -Port 3389",
        "Test-Path -Path C:\\Windows\\SoftwareDistribution",
        "Select-String -Path C:\\Logs\\app.log -Pattern ERROR",
        "Get-ChildItem -Path C:\\Windows\\Temp -File | Measure-Object -Property Length -Sum",
        "Get-Process | Select-Object Name, Id, CPU | Format-Table -AutoSize",
        "Get-Volume | Select-Object DriveLetter, SizeRemaining, Size | Format-List",
        "Get-Counter -Counter \"\\Processor(_Total)\\% Processor Time\" -SampleInterval 2 -MaxSamples 3",
        "ipconfig",
        "ipconfig /all",
        "ipconfig /displaydns",
        "nslookup srv-file-01.corp.example.test",
        "ping -n 4 10.20.0.10",
        "hostname",
    ],
)
def test_read_only_commands_classified_read_only(command: str) -> None:
    assert classify_command(command) == "read_only"


@pytest.mark.parametrize(
    "command",
    [
        # Required mutating verbs & destructive Format-Volume
        "Remove-Item -Path C:\\Windows\\Temp\\* -Recurse -Force",
        "Set-Service -Name dmwappushservice -StartupType Automatic",
        "Stop-Service -Name Spooler -Force",
        "Restart-Service -Name wuauserv -Force",
        "Disable-ADAccount -Identity user01",
        "Clear-DnsClientCache",
        "Format-Volume -DriveLetter D -FileSystem NTFS -Force",
        "Format-Disk -Number 2 -PartitionStyle GPT",
        # Pipes into Invoke-Expression / aliases
        "Get-Content C:\\Temp\\payload.ps1 | Invoke-Expression",
        "Get-Content C:\\Temp\\payload.ps1 | iex",
        "Get-Service -Name Spooler | Stop-Service",
        "Get-Process | Out-File -FilePath C:\\Temp\\procs.txt",
        # Chaining via ;, &&, ||, and newlines
        "Get-Service -Name Spooler; Stop-Service -Name Spooler",
        "Get-Service -Name Spooler && Restart-Service -Name Spooler",
        "Test-Path C:\\Temp || New-Item -ItemType Directory -Path C:\\Temp",
        "Get-Service -Name Spooler\nStop-Service -Name Spooler",
        "Get-Service -Name Spooler\r\nRemove-Item C:\\Temp\\a.txt",
        # Encoded command variants
        "powershell.exe -EncodedCommand SQBFAFgA",
        "pwsh -enc SQBFAFgA",
        "powershell -e SQBFAFgA",
        "Get-Content -Path C:\\foo -EncodedCommand SQBFAFgA",
        "Select-Object -InputObject ([System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('aWV4')))",
        # Bypass tries: subexpressions, parens, scriptblocks, backticks, call operator, redirects, paths
        "Get-Item \"$(Remove-Item C:\\Temp\\secret.txt -Force)\"",
        "Get-Service $(Stop-Service -Name Spooler)",
        "Get-Service -Name (Stop-Service -Name Spooler)",
        "Get-Service | Select-Object @{Name='x';Expression={Stop-Service -Name Spooler}}",
        "G`et-Service -Name Spooler",
        "Get-Content a.txt | I`nvoke-Expression",
        "& 'Remove-Item' C:\\Temp\\file.txt",
        "Get-Process > C:\\Windows\\Temp\\overwrite.txt",
        "Get-Service >> C:\\Windows\\Temp\\append.txt",
        ".\\Get-FakeDiagnostic.ps1",
        "C:\\Temp\\Get-Malicious.exe",
        "\\\\10.20.0.99\\share\\Get-Check.ps1",
        # Mutating flags on allowlisted tools/verbs & malformed input
        "ipconfig /flushdns",
        "ipconfig /release",
        "hostname new-prod-hostname",
        "Test-ComputerSecureChannel -Repair",
        "Get-Service -Name \"UnclosedQuote",
        "",
    ],
)
def test_unsafe_and_bypass_commands_classified_needs_approval(command: str) -> None:
    assert classify_command(command) == "needs_approval"


def test_apply_safety_overrides_overwrites_model_risk_labels() -> None:
    raw = TriageResult(
        likely_cause="Print Spooler hung due to corrupt spool job.",
        confidence="high",
        matched_runbooks=["rb-09-printer-queue-stuck"],
        steps=["Check Spooler service", "Restart Spooler service"],
        commands=[
            CommandItem(
                command="Get-Service -Name Spooler",
                purpose="Check Spooler status",
                risk="needs_approval",  # wrong label from model
            ),
            CommandItem(
                command="Restart-Service -Name Spooler -Force",
                purpose="Restart hung Spooler",
                risk="read_only",  # dangerous wrong label from model
            ),
        ],
        escalate=False,
        escalate_reason=None,
    )

    overridden = apply_safety_overrides(raw)
    assert overridden.commands[0].risk == "read_only"
    assert overridden.commands[1].risk == "needs_approval"


def test_all_runbook_checks_and_fixes_match_expected_risk() -> None:
    index = RunbookIndex.from_directory()
    cmd_re = re.compile(r"^-\s+`(.+)`\s*$")

    for rb in index.runbooks:
        section = None
        for line in rb.body.splitlines():
            stripped = line.strip()
            if stripped.startswith("## Checks"):
                section = "checks"
            elif stripped.startswith("## Fixes"):
                section = "fixes"
            elif stripped.startswith("## "):
                section = "other"
            else:
                match = cmd_re.match(stripped)
                if match and section == "checks":
                    assert classify_command(match.group(1)) == "read_only", (
                        f"Check command in {rb.id} was not read_only: {match.group(1)}"
                    )
                elif match and section == "fixes":
                    assert classify_command(match.group(1)) == "needs_approval", (
                        f"Fix command in {rb.id} was not needs_approval: {match.group(1)}"
                    )
