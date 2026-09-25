# uninstall.ps1 — commitguard Windows uninstaller
#
# Removes the commitguard shim directory from the user PATH.
#
# Usage:
#   cd path\to\commitguard
#   .\uninstall.ps1

#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$shimDir = $PSScriptRoot

Write-Host "[commitguard] Uninstalling..." -ForegroundColor Cyan

$userPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
$entries = $userPath -split ";" | Where-Object { $_ -ne $shimDir -and $_ -ne "" }

if ($entries.Count -eq ($userPath -split ";").Count) {
    Write-Host "[commitguard] Not found in PATH — nothing to remove." -ForegroundColor Yellow
    exit 0
}

$newPath = $entries -join ";"
[System.Environment]::SetEnvironmentVariable("PATH", $newPath, "User")

Write-Host "[commitguard] Removed from User PATH: $shimDir" -ForegroundColor Green
Write-Host "  Restart your terminal for changes to take effect." -ForegroundColor Yellow
