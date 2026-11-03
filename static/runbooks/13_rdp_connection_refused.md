---
id: rb-13-rdp-connection-refused
title: Remote Desktop (RDP) Connection Refused on Windows Server
tags: [rdp, remote-desktop, port-3389, termservice, firewall, mstsc, nla, connection-refused]
---

## Symptoms
- Engineers or authorized users attempting Remote Desktop (`mstsc.exe`) to `srv-rds-01.corp.example.test` receive "Remote Desktop can't connect to the remote computer" over TCP port 3389.
- Host responds to ICMP ping, confirming the OS is online, while TCP 3389 refuses or drops connections.
- Common root cause: stopped Remote Desktop Services (`TermService`), blocked Windows Defender Firewall rule for `Remote Desktop`, or registry flag `fDenyTSConnections` set to `1`.

## Checks (Read-Only Commands)
Test network and TCP port 3389 reachability from a management jump box:
- `Test-NetConnection -ComputerName srv-rds-01.corp.example.test -Port 3389`
Check Remote Desktop Services (`TermService`) and Network Level Authentication (`UmRdpService`) status on the target server via out-of-band console:
- `Get-Service -Name TermService, SessionEnv, UmRdpService | Select-Object Name, Status, StartType`
Inspect Windows Firewall rules for the Remote Desktop rule group:
- `Get-NetFirewallRule -DisplayGroup "Remote Desktop" | Select-Object Name, DisplayName, Enabled, Action, Profile | Format-Table -AutoSize`
Verify the `fDenyTSConnections` registry value (`0` = RDP enabled, `1` = RDP disabled):
- `Get-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server" -Name fDenyTSConnections | Select-Object fDenyTSConnections`

## Fixes (Change Commands)
Enable RDP connections in registry, enable the Windows Firewall Remote Desktop rule group, and start `TermService`:
- `Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" -Value 0`
- `Enable-NetFirewallRule -DisplayGroup "Remote Desktop"`
- `Start-Service -Name TermService`

## Escalation Rule
Escalate to Tier 2 Network/Security Engineering if a Group Policy Object repeatedly reverts RDP or firewall settings, if RD Licensing (`GracePeriod`) has expired on an RDS Session Host, or if perimeter/VLAN ACLs block TCP 3389.
