# install.ps1 — commitguard Windows installer
#
# Run this script once from the commitguard directory.
# It prepends the current directory to the user PATH so that
# git.cmd intercepts all git commands.
#
# Usage:
#   cd path\to\commitguard
#   .\install.ps1

#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$shimDir = $PSScriptRoot

Write-Host "[commitguard] Starting installation..." -ForegroundColor Cyan

# ── 1. Verify Python is available ──────────────────────────────────────────
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error "[commitguard] ERROR: 'python' not found on PATH. Install Python 3.11+ first."
    exit 1
}

$pyVersion = & python --version 2>&1
Write-Host "[commitguard] Found: $pyVersion" -ForegroundColor Green

# ── 2. Verify git_guard.py exists ─────────────────────────────────────────
$guardScript = Join-Path $shimDir "git_guard.py"
if (-not (Test-Path $guardScript)) {
    Write-Error "[commitguard] ERROR: git_guard.py not found in $shimDir"
    exit 1
}

# ── 3. Verify git.cmd shim exists ─────────────────────────────────────────
$shimFile = Join-Path $shimDir "git.cmd"
if (-not (Test-Path $shimFile)) {
    Write-Error "[commitguard] ERROR: git.cmd not found in $shimDir"
    exit 1
}

# ── 4. Read current user PATH ──────────────────────────────────────────────
$userPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
$userPathEntries = $userPath -split ";" | Where-Object { $_ -ne "" }

# Check if already installed
if ($userPathEntries -contains $shimDir) {
    Write-Host "[commitguard] Already installed (directory already in PATH)." -ForegroundColor Yellow
    exit 0
}

# ── 5. Prepend shim directory to user PATH ─────────────────────────────────
$newPath = $shimDir + ";" + $userPath
[System.Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
Write-Host "[commitguard] Prepended to User PATH: $shimDir" -ForegroundColor Green

# ── 6. Verify real git can still be found ─────────────────────────────────
# After PATH change takes effect in a new shell, git_guard.py will
# auto-discover the real git by scanning subsequent PATH entries.
Write-Host "[commitguard] Real git will be auto-discovered by git_guard.py on first use."

# ── 7. Optional: install pyyaml ───────────────────────────────────────────
$yamlInstalled = & python -c "import yaml; print('ok')" 2>$null
if ($yamlInstalled -ne "ok") {
    Write-Host "[commitguard] Tip: pyyaml is not installed. Run: pip install pyyaml" -ForegroundColor Yellow
    Write-Host "              (Required only if you use config.yaml)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[commitguard] Installed successfully." -ForegroundColor Green
Write-Host "  'git' now routes through commitguard." -ForegroundColor Green
Write-Host "  Restart your terminal for PATH changes to take effect." -ForegroundColor Yellow
Write-Host ""
Write-Host "  To uninstall: .\uninstall.ps1"
