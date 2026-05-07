"""数据清理与归档服务。

按 data_retention_days 策略清理：
- 已完成分析的文档原始 content（保留 text_preview）
- 过期的分析任务记录
- 过期的 provider_payloads
- 过期的反馈证据文件
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.config import Settings
from app.db.connection import get_connection_pool

logger = logging.getLogger(__name__)


def run_data_cleanup(settings: Settings) -> dict[str, int]:
    """执行一次数据清理，返回清理计数。"""
    retention = timedelta(days=settings.data_retention_days)
    cutoff = datetime.now(UTC) - retention
    stats: dict[str, int] = {}

    pool = get_connection_pool()
    with pool.connection() as conn:
        # 1. 清理 document_sections 的原始 content（保留 text_preview）
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE document_sections
                SET content = NULL
                WHERE content IS NOT NULL
                  AND id IN (
                      SELECT ds.id
                      FROM document_sections ds
                      JOIN analysis_runs ar ON ar.document_id = ds.document_id
                      WHERE ar.status = 'completed'
                        AND ar.finished_at < %s
                  )
                """,
                (cutoff,),
            )
            stats["sections_content_cleared"] = cur.rowcount

        # 2. 清理过期的 provider_payloads（保留最近 N 天）
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM provider_payloads
                WHERE created_at < %s
                """,
                (cutoff,),
            )
            stats["provider_payloads_deleted"] = cur.rowcount

        # 3. 清理过期的 analysis_tasks（保留最近 N 天）
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM analysis_tasks
                WHERE status IN ('completed', 'failed')
                  AND finished_at < %s
                """,
                (cutoff,),
            )
            stats["analysis_tasks_deleted"] = cur.rowcount

        # 4. 清理过期的原始上传文件
        upload_dir = Path(settings.upload_storage_dir)
        if upload_dir.exists():
            deleted_files = 0
            for f in upload_dir.iterdir():
                if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime, tz=UTC) < cutoff:
                    try:
                        f.unlink()
                        deleted_files += 1
                    except OSError:
                        pass
            stats["upload_files_deleted"] = deleted_files

        # 5. 清理过期的反馈证据文件
        feedback_dir = Path(settings.feedback_storage_dir)
        if feedback_dir.exists():
            deleted_files = 0
            for f in feedback_dir.iterdir():
                if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime, tz=UTC) < cutoff:
                    try:
                        f.unlink()
                        deleted_files += 1
                    except OSError:
                        pass
            stats["feedback_files_deleted"] = deleted_files

        conn.commit()

    total = sum(stats.values())
    if total > 0:
        logger.info("Data cleanup completed: %s", stats)
    return stats
