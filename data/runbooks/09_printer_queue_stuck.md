---
id: rb-09-printer-queue-stuck
title: Windows Print Queue and Print Spooler Stuck
tags: [printer, print-queue, spooler, printing, stuck-job, print-server]
---

## Symptoms
- Print jobs sent to shared office printer `PRN-FL2-01` remain stuck in `Printing` or `Deleting` status and block all subsequent documents in the queue.
- Print Spooler (`Spooler`) service hangs or crashes repeatedly with corrupt `.SPL` / `.SHD` spool files in `C:\Windows\System32\spool\PRINTERS`.
- Common root cause: corrupted print job file inside the spool folder or hung vendor Type-3 print driver stalling the `Spooler` service.

## Checks (Read-Only Commands)
Check the status of the Windows Print Spooler service:
- `Get-Service -Name Spooler | Select-Object Name, Status, StartType`
List printers and current queued job counts:
- `Get-Printer | Select-Object Name, DriverName, PortName, PrinterStatus, JobCount | Format-Table -AutoSize`
Inspect individual jobs stuck in the affected printer queue:
- `Get-PrintJob -PrinterName "PRN-FL2-01" | Select-Object Id, DocumentName, UserName, JobStatus, SubmittedTime`

## Fixes (Change Commands)
Stop the Print Spooler service, purge corrupt spool files from the `PRINTERS` spool folder, and start the Print Spooler service:
- `Stop-Service -Name Spooler -Force`
- `Remove-Item -Path "C:\Windows\System32\spool\PRINTERS\*" -Force`
- `Start-Service -Name Spooler`

## Escalation Rule
Escalate to Tier 2 Endpoint/Server Engineering if a faulty kernel/Type-3 print driver causes recurring `spoolsv.exe` crashes (`Event ID 1000` in Application log) requiring driver replacement across GPO-deployed print queues.
