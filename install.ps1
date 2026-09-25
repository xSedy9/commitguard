# install.ps1 — commitguard Windows installer
#
# Run this script once from the commitguard directory.
# Prepends the directory to PATH so git.cmd intercepts all git commands.
#
# Usage:
#   cd path\to\commitguard
#   powershell -ExecutionPolicy Bypass -File .\install.ps1

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

# ── 4. Check for Administrator privileges & System Git ─────────────────────
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$machinePath = [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
$hasSystemGit = $false
foreach ($p in ($machinePath -split ";")) {
    if ($p -and (Test-Path (Join-Path $p "git.exe") -ErrorAction SilentlyContinue)) {
        $hasSystemGit = $true
        break
    }
}

if ($hasSystemGit -and -not $isAdmin) {
    Write-Host "[commitguard] NOTICE: Real git is installed in System PATH (Machine scope)." -ForegroundColor Yellow
    Write-Host "[commitguard] In Windows, System PATH has higher priority than User PATH." -ForegroundColor Yellow
    Write-Host "[commitguard] To intercept 'git' globally across all terminals, IDEs, and tools," -ForegroundColor Yellow
    Write-Host "[commitguard] commitguard must be added to System PATH (requires Administrator elevation)." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "[commitguard] Requesting Administrator elevation..." -ForegroundColor Cyan
    Start-Process powershell -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit 0
}

# ── 5. Prepend to PATH ─────────────────────────────────────────────────────
if ($isAdmin) {
    $machineEntries = $machinePath -split ";" | Where-Object { $_ -ne "" }
    if ($machineEntries -notcontains $shimDir) {
        $newMachinePath = $shimDir + ";" + $machinePath
        [System.Environment]::SetEnvironmentVariable("PATH", $newMachinePath, "Machine")
        Write-Host "[commitguard] Prepended to System (Machine) PATH: $shimDir" -ForegroundColor Green
    } else {
        Write-Host "[commitguard] Already in System PATH." -ForegroundColor Yellow
    }
} else {
    $userPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
    $userPathEntries = $userPath -split ";" | Where-Object { $_ -ne "" }
    if ($userPathEntries -notcontains $shimDir) {
        $newPath = $shimDir + ";" + $userPath
        [System.Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
        Write-Host "[commitguard] Prepended to User PATH: $shimDir" -ForegroundColor Green
    } else {
        Write-Host "[commitguard] Already in User PATH." -ForegroundColor Yellow
    }
}

# ── 6. Auto-discover verification ──────────────────────────────────────────
Write-Host "[commitguard] Real git will be auto-discovered by git_guard.py on first use."

# ── 7. Optional: install pyyaml ───────────────────────────────────────────
try {
    $yamlInstalled = & python -c "import yaml; print('ok')" 2>&1
} catch {
    $yamlInstalled = ""
}
if ($yamlInstalled -notmatch "ok") {
    Write-Host "[commitguard] Installing pyyaml..." -ForegroundColor Yellow
    & python -m pip install pyyaml --quiet
}

Write-Host ""
Write-Host "[commitguard] Installed successfully." -ForegroundColor Green
Write-Host "  'git' now routes through commitguard globally." -ForegroundColor Green
Write-Host "  Restart your terminal / editor for PATH changes to take effect." -ForegroundColor Yellow
Write-Host ""
Write-Host "  To uninstall: .\uninstall.ps1"
