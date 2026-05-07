$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeDir = Join-Path $projectRoot ".dev"
$workerPidFile = Join-Path $runtimeDir "worker.pid"
$workerLog = Join-Path $runtimeDir "worker.log"
$workerErrLog = Join-Path $runtimeDir "worker.err.log"
$queueName = if ($env:AI_RATE_CELERY_QUEUE_NAME) { $env:AI_RATE_CELERY_QUEUE_NAME } else { "analysis" }

New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

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

function Resolve-PythonBootstrap {
    $pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        return @{
            FilePath = $pyLauncher.Source
            Arguments = @("-3.11", "-m", "venv", (Join-Path $projectRoot ".venv"))
        }
    }

    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $python) {
        throw "Python was not found. Install Python 3.11 and try again."
    }

    return @{
        FilePath = $python.Source
        Arguments = @("-m", "venv", (Join-Path $projectRoot ".venv"))
    }
}

function Ensure-BackendPython {
    $venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        $bootstrap = Resolve-PythonBootstrap
        Write-Step "Creating Python virtual environment .venv"
        & $bootstrap.FilePath @($bootstrap.Arguments)
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create the Python virtual environment."
        }
    }

    return $venvPython
}

function Ensure-BackendDependencies {
    param([string]$PythonExe)

    & $PythonExe -c "import fastapi, uvicorn, pydantic, celery" *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Step "Installing backend dependencies"
        & $PythonExe -m pip install -r (Join-Path $projectRoot "requirements.txt")
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install backend dependencies."
        }
    }
}

if (Test-Path $workerPidFile) {
    try {
        $existing = Get-Process -Id ([int](Get-Content $workerPidFile -Raw).Trim()) -ErrorAction Stop
        Write-Step "Worker is already running (PID $($existing.Id)), skipping"
        exit 0
    }
    catch {
        Remove-Item $workerPidFile -Force -ErrorAction SilentlyContinue
    }
}

$pythonExe = Ensure-BackendPython
Ensure-BackendDependencies -PythonExe $pythonExe

Remove-Item $workerLog -Force -ErrorAction SilentlyContinue
Remove-Item $workerErrLog -Force -ErrorAction SilentlyContinue

$arguments = @(
    "-m", "celery",
    "-A", "app.worker.celery_app",
    "worker",
    "--loglevel=info",
    "--pool=solo",
    "--queues=$queueName"
)

$process = Start-Process `
    -FilePath $pythonExe `
    -ArgumentList $arguments `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $workerLog `
    -RedirectStandardError $workerErrLog `
    -PassThru

Set-Content -Path $workerPidFile -Value $process.Id -Encoding ascii
Start-Sleep -Seconds 3

if ($process.HasExited) {
    $stdout = if (Test-Path $workerLog) { Get-Content $workerLog -Raw } else { "" }
    $stderr = if (Test-Path $workerErrLog) { Get-Content $workerErrLog -Raw } else { "" }
    throw "Celery worker failed to start.`n--- stdout ---`n$stdout`n--- stderr ---`n$stderr"
}

Write-Step "Celery worker started (PID $($process.Id), queue $queueName)"
Write-Host "Remember to set AI_RATE_ASYNC_QUEUE_BACKEND=celery before starting the API." -ForegroundColor Yellow
