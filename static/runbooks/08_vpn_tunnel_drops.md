---
id: rb-08-vpn-tunnel-drops
title: Remote Access VPN Connection Drops Repeatedly
tags: [vpn, remote-access, ikev2, sstp, disconnect, mtu, tunnel, rasman]
---

## Symptoms
- Remote worker's Windows built-in IKEv2/SSTP VPN tunnel (`Corp-SplitVPN`) disconnects every 5–15 minutes or drops under heavy file transfer.
- RasClient event log records `Event ID 20227`, `829`, or dead-peer detection / MTU fragmentation drops toward `vpn-gw.tenant-alpha.test`.
- Common root cause: UDP 500/4500 NAT keepalive timeout, oversized VPN interface MTU causing packet fragmentation, or unstable `RasMan` (Remote Access Connection Manager) state.

## Checks (Read-Only Commands)
Inspect configured Windows VPN profiles and current tunnel status:
- `Get-VpnConnection | Select-Object Name, ServerAddress, TunnelType, ConnectionStatus, SplitTunneling`
Test reachability and packet loss to the public VPN gateway endpoint:
- `ping -n 10 vpn-gw.tenant-alpha.test`
Verify TCP/443 reachability to the VPN gateway for SSTP fallback:
- `Test-NetConnection -ComputerName vpn-gw.tenant-alpha.test -Port 443`
Check Remote Access Connection Manager service state and recent RasClient operational events:
- `Get-Service -Name RasMan, PolicyAgent | Select-Object Name, Status, StartType`

## Fixes (Change Commands)
Restart the Remote Access Connection Manager service and adjust the VPN profile or network interface MTU after approval:
- `Restart-Service -Name RasMan -Force`
- `Set-VpnConnection -Name "Corp-SplitVPN" -IdleDisconnectSeconds 1800`

## Escalation Rule
Escalate to Tier 2 Firewall/Network Engineering if multiple remote users drop simultaneously (indicating head-end firewall gateway exhaustion or ISP circuit flapping) or if NPS/RADIUS certificate authentication fails globally.
