---
id: rb-16-ad-password-reset
title: Active Directory Forgotten or Expired Password Reset
tags: [password-reset, password-expired, active-directory, ad, credentials, must-change-password]
---

## Symptoms
- Domain user `user08@corp.example.test` cannot sign in due to an expired domain password ("Your password has expired and must be changed") or forgotten password while working remotely.
- Remote VPN users cannot complete Ctrl+Alt+Del password change before establishing tunnel connectivity.
- Common root cause: domain maximum password age policy (`90 days`) reached while off-network, or user forgot current AD password.

## Checks (Read-Only Commands)
Inspect the account's password age, expiration status, lockout flag, and enabled status in Active Directory:
- `Get-ADUser -Identity user08 -Properties Enabled, LockedOut, PasswordLastSet, PasswordExpired, PasswordNeverExpires, CannotChangePassword | Select-Object SamAccountName, Enabled, LockedOut, PasswordLastSet, PasswordExpired, PasswordNeverExpires`
Check the domain default password policy settings for max age and complexity requirements:
- `Get-ADDefaultDomainPasswordPolicy | Select-Object ComplexityEnabled, MinPasswordLength, MaxPasswordAge, LockoutThreshold`

## Fixes (Change Commands)
After completing out-of-band MFA/callback identity verification, set a temporary password and require change at next logon (or coordinate VPN pre-logon password change):
- `Set-ADAccountPassword -Identity user08 -Reset`
- `Set-ADUser -Identity user08 -ChangePasswordAtLogon $true`

## Escalation Rule
Escalate immediately to Tier 2 Security Operations if the caller fails identity/MFA verification challenge, if the request targets a Domain Admin / Enterprise Admin / service account, or if Entra Connect password hash sync fails to replicate.
