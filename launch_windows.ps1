# PowerShell launcher: does not create a CMD batch-job Ctrl+C prompt.
param(
    [string]$Cores = "auto",
    [int]$Port = 8765,
    [string]$HostAddress = "127.0.0.1"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$LocalPython = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $LocalPython) {
    $Python = $LocalPython
} else {
    $Python = (Get-Command python -ErrorAction Stop).Source
}
Write-Host "Starting NeuroSkin 3 on $HostAddress`:$Port with $Cores CPU workers"
Write-Host "Ctrl+C stops the parent server; spawned Python workers ignore console SIGINT."
& $Python (Join-Path $Root "server.py") --host $HostAddress --port $Port --cores $Cores --open
$Code = $LASTEXITCODE
if ($null -eq $Code) { $Code = 0 }
exit $Code
