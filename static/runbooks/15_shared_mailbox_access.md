---
id: rb-15-shared-mailbox-access
title: Microsoft 365 Shared Mailbox Access Denied or Missing in Outlook
tags: [shared-mailbox, m365, exchange-online, outlook, fullaccess, sendas, permissions, automapping]
---

## Symptoms
- User `user05@tenant-alpha.test` cannot open shared mailbox `billing@tenant-alpha.test` in Outlook or Outlook on the Web ("Cannot display the folder / You don't have permission").
- Alternatively, user can read messages in the shared mailbox yet receives `5.7.60 SMTP; Client does not have permissions to send as this sender` when replying.
- Common root cause: missing `FullAccess` mailbox permission, missing `SendAs` recipient permission in Exchange Online, or broken Outlook AutoMapping requiring permission refresh.

## Checks (Read-Only Commands)
Confirm the target mailbox exists and is configured as a `SharedMailbox`:
- `Get-EXOMailbox -Identity billing@tenant-alpha.test | Select-Object DisplayName, PrimarySmtpAddress, RecipientTypeDetails`
Check existing `FullAccess` permissions on the shared mailbox:
- `Get-EXOMailboxPermission -Identity billing@tenant-alpha.test | Select-Object User, AccessRights, IsInherited`
Check existing `SendAs` permissions on the shared mailbox:
- `Get-EXORecipientPermission -Identity billing@tenant-alpha.test | Select-Object Trustee, AccessControlType, AccessRights`

## Fixes (Change Commands)
Grant `FullAccess` (with AutoMapping) and/or `SendAs` permission after verifying written manager approval from the mailbox owner:
- `Add-MailboxPermission -Identity billing@tenant-alpha.test -User user05@tenant-alpha.test -AccessRights FullAccess -AutoMapping $true`
- `Add-RecipientPermission -Identity billing@tenant-alpha.test -Trustee user05@tenant-alpha.test -AccessRights SendAs -Confirm:$false`

## Escalation Rule
Escalate to Tier 2 Messaging/Compliance Admin if written approval from the department owner is missing, if permissions relate to executive/HR/legal compliance mailboxes under litigation hold, or if hybrid on-premises AD sync blocks cloud permission inheritance.
