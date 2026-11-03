---
id: rb-07-dns-resolution-failure
title: Internal or External DNS Resolution Failure
tags: [dns, name-resolution, nslookup, forwarder, dns-cache, nxdomain, network]
---

## Symptoms
- Workstations or member servers cannot resolve internal Active Directory FQDNs (`srv-file-01.corp.example.test`) or external web hosts, while raw IP `ping` succeeds.
- Browsers show `DNS_PROBE_FINISHED_NXDOMAIN` and domain-joined resources fail to map.
- Common root cause: NIC pointing to public DNS instead of internal AD DNS servers, poisoned/stale local DNS client resolver cache, or stopped `Dnscache` / `DNS` server service.

## Checks (Read-Only Commands)
Display full network adapter and configured DNS server details:
- `ipconfig /all`
Inspect configured IPv4 DNS server addresses per interface:
- `Get-DnsClientServerAddress -AddressFamily IPv4 | Select-Object InterfaceAlias, ServerAddresses`
Test DNS name lookup against the default DNS server:
- `nslookup srv-file-01.corp.example.test`
Verify IP reachability to the primary internal DNS server (`10.20.0.10`):
- `ping -n 4 10.20.0.10`

## Fixes (Change Commands)
Flush the local DNS resolver cache and point the workstation NIC back to approved internal AD DNS servers:
- `Clear-DnsClientCache`
- `Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses "10.20.0.10","10.20.0.11"`

## Escalation Rule
Escalate to Tier 2 Network/AD Engineering if the Domain Controller `DNS` service itself fails to start, if Active Directory-integrated DNS zone replication fails, or if upstream ISP/root DNS forwarders time out across an entire site.
