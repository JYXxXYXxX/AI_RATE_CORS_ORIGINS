$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeDir = Join-Path $projectRoot ".dev"

function Write-Step {
    param([string]$Message)

    Write-Host "[dev] $Message" -ForegroundColor Cyan
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

function Stop-ManagedService {
    param(
        [string]$Name,
        [string]$PidFile
    )

    if (-not (Test-Path $PidFile)) {
        Write-Step "$Name has no managed process"
        return
    }

    $rawPid = (Get-Content $PidFile -Raw).Trim()
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue

    if (-not $rawPid) {
        Write-Step "$Name PID file was empty and has been cleaned up"
        return
    }

    try {
        $process = Get-Process -Id ([int]$rawPid) -ErrorAction Stop
        Stop-ProcessTree -ProcessId $process.Id
        Write-Step "$Name stopped (PID $($process.Id))"
    }
    catch {
        Write-Step "$Name process was not found and the PID file was cleaned up"
    }
}

Stop-ManagedService -Name "frontend" -PidFile (Join-Path $runtimeDir "frontend.pid")
Stop-ManagedService -Name "backend" -PidFile (Join-Path $runtimeDir "backend.pid")
