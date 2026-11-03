---
id: rb-02-ad-account-locked
title: Locked Active Directory User Account
tags: [active-directory, ad, lockout, locked-out, authentication, event-4740, login]
---

## Symptoms
- Domain user (`user01@corp.example.test`) receives "The referenced account is currently locked out and may not be logged on to" when signing into Windows, VPN, or Outlook.
- Domain Controller Security log records `Event ID 4740` identifying the caller workstation or RDS host submitting stale cached credentials.
- Common root cause: stale saved password in Windows Credential Manager, disconnected RDP session, or mobile mail client after a recent password change.

## Checks (Read-Only Commands)
Check whether the Active Directory account is locked out and inspect bad password attempt counters:
- `Get-ADUser -Identity user01 -Properties LockedOut, AccountLockoutTime, BadPwdCount, LastBadPasswordAttempt | Select-Object SamAccountName, LockedOut, AccountLockoutTime, BadPwdCount, LastBadPasswordAttempt`
Review recent `Event ID 4740` lockout events in the Domain Controller Security log:
- `Get-WinEvent -LogName Security -MaxEvents 40 | Select-Object TimeCreated, Id, Message | Format-List`

## Fixes (Change Commands)
Unlock the Active Directory user account after verifying user identity per service desk verification policy:
- `Unlock-ADAccount -Identity user01`
Clear cached credentials or force logoff of stale sessions if needed on the source workstation:
- `Clear-RecycleBin -Confirm`

## Escalation Rule
Escalate immediately to Tier 2 Security Operations if lockouts recur from unknown external IPs, if multiple accounts lock out simultaneously (potential password-spray attack), or if a privileged administrator/service account is locked out.
