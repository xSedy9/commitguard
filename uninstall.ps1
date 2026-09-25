# uninstall.ps1 — commitguard Windows uninstaller
#
# Removes the commitguard shim directory from User and System PATH.
#
# Usage:
#   cd path\to\commitguard
#   powershell -ExecutionPolicy Bypass -File .\uninstall.ps1

#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$shimDir = $PSScriptRoot

Write-Host "[commitguard] Uninstalling..." -ForegroundColor Cyan

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

# 1. Remove from User PATH
$userPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath) {
    $entries = $userPath -split ";" | Where-Object { $_ -ne $shimDir -and $_ -ne "" }
    $newPath = $entries -join ";"
    [System.Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
}

# 2. Remove from Machine PATH if present / admin
$machinePath = [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
if ($machinePath -and ($machinePath -split ";" -contains $shimDir)) {
    if ($isAdmin) {
        $mEntries = $machinePath -split ";" | Where-Object { $_ -ne $shimDir -and $_ -ne "" }
        $newMPath = $mEntries -join ";"
        [System.Environment]::SetEnvironmentVariable("PATH", $newMPath, "Machine")
        Write-Host "[commitguard] Removed from System PATH: $shimDir" -ForegroundColor Green
    } else {
        Write-Host "[commitguard] Requesting Administrator elevation to remove from System PATH..." -ForegroundColor Cyan
        Start-Process powershell -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`""
        exit 0
    }
}

Write-Host "[commitguard] Removed from PATH." -ForegroundColor Green
Write-Host "  Restart your terminal for changes to take effect." -ForegroundColor Yellow
