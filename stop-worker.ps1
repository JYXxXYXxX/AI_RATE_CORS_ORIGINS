$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeDir = Join-Path $projectRoot ".dev"
$workerPidFile = Join-Path $runtimeDir "worker.pid"

function Write-Step {
    param([string]$Message)

    Write-Host "[worker] $Message" -ForegroundColor Cyan
}

function Stop-ProcessTree {
    param([int]$ProcessId)

    $taskkill = Get-Command taskkill.exe -ErrorAction SilentlyContinue
    if ($taskkill) {
        & $taskkill.Source "/PID" $ProcessId "/T" "/F" *> $null
        return
    }

    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

if (-not (Test-Path $workerPidFile)) {
    Write-Step "Worker has no managed process"
    exit 0
}

$rawPid = (Get-Content $workerPidFile -Raw).Trim()
Remove-Item $workerPidFile -Force -ErrorAction SilentlyContinue

if (-not $rawPid) {
    Write-Step "Worker PID file was empty and has been cleaned up"
    exit 0
}

try {
    $process = Get-Process -Id ([int]$rawPid) -ErrorAction Stop
    Stop-ProcessTree -ProcessId $process.Id
    Write-Step "Worker stopped (PID $($process.Id))"
}
catch {
    Write-Step "Worker process was not found and the PID file was cleaned up"
}
