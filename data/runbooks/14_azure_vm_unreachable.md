---
id: rb-14-azure-vm-unreachable
title: Azure Virtual Machine Unreachable Over Network
tags: [azure, azure-vm, cloud, unreachable, nsg, deallocated, boot-diagnostics, vnet]
---

## Symptoms
- Cloud server `az-vm-web-01` in Azure resource group `rg-prod-alpha` stops responding to HTTPS, SSH/RDP, and internal site-to-site VPN traffic.
- Monitoring reports 100% packet loss to the Azure VM's private or public IP.
- Common root cause: VM in `Stopped (deallocated)` power state, Network Security Group (NSG) deny rule blocking inbound traffic, or failed guest OS boot visible in Azure Boot Diagnostics.

## Checks (Read-Only Commands)
Query the Azure VM provisioning and runtime power state via Az PowerShell:
- `Get-AzVM -ResourceGroupName "rg-prod-alpha" -Name "az-vm-web-01" -Status | Select-Object Name, PowerState, ProvisioningState`
Inspect Network Security Group rules attached to the resource group for unintended inbound deny rules:
- `Get-AzNetworkSecurityGroup -ResourceGroupName "rg-prod-alpha" | Select-Object Name, ProvisioningState, SecurityRules`
Test TCP connectivity from the hybrid jump host to the Azure VM private IP (`10.50.1.15`):
- `Test-NetConnection -ComputerName 10.50.1.15 -Port 443`

## Fixes (Change Commands)
Start or restart the Azure VM if deallocated/hung after change approval:
- `Start-AzVM -ResourceGroupName "rg-prod-alpha" -Name "az-vm-web-01"`
- `Restart-AzVM -ResourceGroupName "rg-prod-alpha" -Name "az-vm-web-01"`

## Escalation Rule
Escalate to Tier 2 Cloud Architecture Engineering if Azure Resource Health reports platform host degradation, if ExpressRoute / Site-to-Site VPN BGP routes are down, or if Boot Diagnostics shows a guest OS BSOD/boot loop requiring OS disk swap recovery.
