#!/bin/bash
# 数据库备份脚本（Bash）
# 用法: ./scripts/backup_db.sh
# 环境变量: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_DB, POSTGRES_PASSWORD, BACKUP_DIR

set -euo pipefail

HOST="${POSTGRES_HOST:-localhost}"
PORT="${POSTGRES_PORT:-5432}"
USER="${POSTGRES_USER:-postgres}"
DB="${POSTGRES_DB:-paper_risk_platform}"
BACKUP_DIR="${BACKUP_DIR:-data/backups}"
PASSWORD="${POSTGRES_PASSWORD:-postgres}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTFILE="${BACKUP_DIR}/${DB}_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

echo "Backing up $DB to $OUTFILE ..."
PGPASSWORD="$PASSWORD" pg_dump -h "$HOST" -p "$PORT" -U "$USER" -d "$DB" -f "$OUTFILE"

echo "Backup completed: $OUTFILE"

# 保留最近 30 天的备份
find "$BACKUP_DIR" -name "${DB}_*.sql" -mtime +30 -delete
