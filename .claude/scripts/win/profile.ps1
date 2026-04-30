# Windows PowerShell wrapper for profile.py
# Equivalent to `bash .claude/scripts/profile.sh <args>` on macOS/Linux.
#
# Usage:
#   .\profile.ps1 get
#   .\profile.ps1 show
#   .\profile.ps1 set retail
#   .\profile.ps1 stale
#   .\profile.ps1 validate

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PyScript = Join-Path $ScriptDir "..\profile.py" | Resolve-Path | Select-Object -ExpandProperty Path

# Find Python (prefer python over python3 on Windows)
$PyCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PyCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PyCmd = "python3"
} else {
    Write-Error "Python not found in PATH. Install Python 3.9+ from python.org or Microsoft Store."
    exit 99
}

& $PyCmd $PyScript $args
exit $LASTEXITCODE
