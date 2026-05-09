param(
    [switch]$ReinstallBackend,
    [switch]$ReinstallFrontend
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendDir = Join-Path $projectRoot "frontend"
$runtimeDir = Join-Path $projectRoot ".dev"
$backendPidFile = Join-Path $runtimeDir "backend.pid"
$frontendPidFile = Join-Path $runtimeDir "frontend.pid"
$backendLog = Join-Path $runtimeDir "backend.log"
$backendErrLog = Join-Path $runtimeDir "backend.err.log"
$frontendLog = Join-Path $runtimeDir "frontend.log"
$frontendErrLog = Join-Path $runtimeDir "frontend.err.log"

New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

function Write-Step {
    param([string]$Message)

    Write-Host "[dev] $Message" -ForegroundColor Cyan
}

function Get-ManagedProcess {
    param([string]$PidFile)

    if (-not (Test-Path $PidFile)) {
        return $null
    }

    $rawContent = Get-Content $PidFile -Raw -ErrorAction SilentlyContinue
    if (-not $rawContent) {
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        return $null
    }

    $rawPid = $rawContent.Trim()
    if (-not $rawPid) {
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        return $null
    }

    try {
        return Get-Process -Id ([int]$rawPid) -ErrorAction Stop
    }
    catch {
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        return $null
    }
}

function Test-HttpEndpoint {
    param([string]$Url)

    try {
        $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
        if ($curl) {
            & $curl.Source "--silent" "--output" "NUL" "--fail" $Url 2>$null
            return $LASTEXITCODE -eq 0
        }

        $invokeParams = @{
            Uri = $Url
            TimeoutSec = 3
            ErrorAction = "Stop"
        }

        if ((Get-Command Invoke-WebRequest).Parameters.ContainsKey("UseBasicParsing")) {
            $invokeParams.UseBasicParsing = $true
        }

        $null = Invoke-WebRequest @invokeParams
        return $true
    }
    catch {
        return $false
    }
}

function Wait-ForHttpEndpoint {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpEndpoint -Url $Url) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }

    return $false
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

    $pythonPath = $python.Source
    $versionCheckArgs = @("-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)")
    & $pythonPath @versionCheckArgs
    if ($LASTEXITCODE -ne 0) {
        throw "The default Python version is lower than 3.10. Install Python 3.11 and try again."
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
        $bootstrapPath = $bootstrap.FilePath
        Write-Step "Creating Python virtual environment .venv"
        & $bootstrapPath @($bootstrap.Arguments)
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create the Python virtual environment."
        }
    }

    return $venvPython
}

function Ensure-BackendDependencies {
    param([string]$PythonExe)

    $needsInstall = $ReinstallBackend
    if (-not $needsInstall) {
        $importCheckArgs = @("-c", "import fastapi, uvicorn, pydantic")
        & $PythonExe @importCheckArgs *> $null
        $needsInstall = $LASTEXITCODE -ne 0
    }

    if ($needsInstall) {
        Write-Step "Installing backend dependencies"
        $pipInstallArgs = @("-m", "pip", "install", "-r", (Join-Path $projectRoot "requirements.txt"))
        & $PythonExe @pipInstallArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install backend dependencies."
        }
    }
}

function Resolve-NpmCmd {
    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npm) {
        throw "npm.cmd was not found. Install the Windows version of Node.js and try again."
    }

    return $npm.Source
}

function Ensure-FrontendDependencies {
    param([string]$NpmCmd)

    $nodeModulesDir = Join-Path $frontendDir "node_modules"
    if ($ReinstallFrontend -and (Test-Path $nodeModulesDir)) {
        Write-Step "Removing the old frontend dependency directory"
        Remove-Item $nodeModulesDir -Recurse -Force
    }

    $needsInstall = $ReinstallFrontend -or -not (Test-Path $nodeModulesDir)
    if ($needsInstall) {
        Write-Step "Installing frontend dependencies"
        & $NpmCmd "--script-shell=$env:ComSpec" install
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install frontend dependencies."
        }
    }
}

function Start-ManagedService {
    param(
        [string]$Name,
        [string]$HealthUrl,
        [string]$PidFile,
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [string]$StdOutLog,
        [string]$StdErrLog,
        [int]$TimeoutSeconds = 30
    )

    if (Test-HttpEndpoint -Url $HealthUrl) {
        Write-Step "$Name is already running, skipping"
        return
    }

    $existingProcess = Get-ManagedProcess -PidFile $PidFile
    if ($existingProcess) {
        Stop-ProcessTree -ProcessId $existingProcess.Id
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    }

    Remove-Item $StdOutLog -Force -ErrorAction SilentlyContinue
    Remove-Item $StdErrLog -Force -ErrorAction SilentlyContinue

    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $StdOutLog `
        -RedirectStandardError $StdErrLog `
        -PassThru

    Set-Content -Path $PidFile -Value $process.Id -Encoding ascii

    if (-not (Wait-ForHttpEndpoint -Url $HealthUrl -TimeoutSeconds $TimeoutSeconds)) {
        if (-not $process.HasExited) {
            Stop-ProcessTree -ProcessId $process.Id
        }

        $stdout = if (Test-Path $StdOutLog) { Get-Content $StdOutLog -Raw } else { "" }
        $stderr = if (Test-Path $StdErrLog) { Get-Content $StdErrLog -Raw } else { "" }
        throw "$Name failed to start.`n--- stdout ---`n$stdout`n--- stderr ---`n$stderr"
    }

    $process.Dispose()
    Write-Step "$Name started"
}

$pythonExe = Ensure-BackendPython
Ensure-BackendDependencies -PythonExe $pythonExe

$npmCmd = Resolve-NpmCmd
Ensure-FrontendDependencies -NpmCmd $npmCmd

Start-ManagedService `
    -Name "backend" `
    -HealthUrl "http://127.0.0.1:8010/health" `
    -PidFile $backendPidFile `
    -FilePath $pythonExe `
    -Arguments @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010", "--reload") `
    -WorkingDirectory $projectRoot `
    -StdOutLog $backendLog `
    -StdErrLog $backendErrLog `
    -TimeoutSeconds 30

Start-ManagedService `
    -Name "frontend" `
    -HealthUrl "http://127.0.0.1:3000/" `
    -PidFile $frontendPidFile `
    -FilePath $npmCmd `
    -Arguments @("--script-shell=$env:ComSpec", "run", "dev", "--", "--strictPort") `
    -WorkingDirectory $frontendDir `
    -StdOutLog $frontendLog `
    -StdErrLog $frontendErrLog `
    -TimeoutSeconds 30

Write-Host ""
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Green
Write-Host "Backend:  http://localhost:8010/docs" -ForegroundColor Green
Write-Host "Mode:     free closed-loop demo (anonymous upload enabled)" -ForegroundColor Green
Write-Host "Logs:     $runtimeDir" -ForegroundColor DarkGray
Write-Host "Tip:      open the frontend and upload a paper directly, no login required" -ForegroundColor DarkGray


