# 数据库备份脚本（PowerShell）
# 用法: .\scripts\backup_db.ps1
# 环境变量: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_DB, BACKUP_DIR

$ErrorActionPreference = "Stop"

$host_env     = $env:POSTGRES_HOST -or "localhost"
$port_env     = $env:POSTGRES_PORT -or "5432"
$user_env     = $env:POSTGRES_USER -or "postgres"
$db_env       = $env:POSTGRES_DB   -or "paper_risk_platform"
$backup_dir   = $env:BACKUP_DIR    -or "data/backups"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$filename = "${db_env}_${timestamp}.sql"
$outfile = Join-Path $backup_dir $filename

if (-not (Test-Path $backup_dir)) {
    New-Item -ItemType Directory -Path $backup_dir -Force | Out-Null
}

Write-Host "Backing up $db_env to $outfile ..."
$env:PGPASSWORD = $env:POSTGRES_PASSWORD -or "postgres"
& pg_dump -h $host_env -p $port_env -U $user_env -d $db_env -f $outfile

if ($LASTEXITCODE -eq 0) {
    Write-Host "Backup completed: $outfile"
    # 保留最近 30 天的备份
    Get-ChildItem -Path $backup_dir -Filter "${db_env}_*.sql" |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
        Remove-Item -Force
} else {
    Write-Error "Backup failed"
}
