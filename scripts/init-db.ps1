$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

param(
    [string]$DatabaseUrl = "postgresql://postgres:postgres@localhost:5432/paper_risk_platform"
)

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$schemaPath = Join-Path $projectRoot "sql\schema.sql"

if (-not (Test-Path $schemaPath)) {
    throw "Schema file not found: $schemaPath"
}

$psql = Get-Command psql.exe -ErrorAction SilentlyContinue
if (-not $psql) {
    throw "psql.exe was not found. Install PostgreSQL client tools first."
}

Write-Host "[db] Applying schema: $schemaPath" -ForegroundColor Cyan
& $psql.Source "--dbname=$DatabaseUrl" "-v" "ON_ERROR_STOP=1" "-f" $schemaPath

if ($LASTEXITCODE -ne 0) {
    throw "Database schema initialization failed."
}

Write-Host "[db] Schema applied successfully." -ForegroundColor Green
