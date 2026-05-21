from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from app.db.connection import get_connection_pool


def get_repository() -> "UnifiedRepository":
    return UnifiedRepository(get_connection_pool())


def _strip_nul_bytes(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, dict):
        return {key: _strip_nul_bytes(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_strip_nul_bytes(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_strip_nul_bytes(item) for item in value)
    return value


class UnifiedRepository:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def health_check(self) -> bool:
        """验证数据库连接是否可用。"""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return cur.fetchone() is not None

    def upsert_document(
        self,
        *,
        title: str | None,
        filename: str,
        subject: str | None,
        degree_level: str | None,
        language: str,
        doc_hash: str,
        char_count: int,
        source_type: str,
        original_file_path: str,
        cleaned_text_path: str,
    ) -> dict[str, Any]:
        query = """
            INSERT INTO documents (
                title,
                filename,
                subject,
                degree_level,
                language,
                doc_hash,
                char_count,
                section_count,
                status,
                source_type,
                original_file_path,
                cleaned_text_path
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 'uploaded', %s, %s, %s)
            ON CONFLICT (doc_hash) DO UPDATE
            SET
                title = COALESCE(EXCLUDED.title, documents.title),
                filename = EXCLUDED.filename,
                subject = COALESCE(EXCLUDED.subject, documents.subject),
                degree_level = COALESCE(EXCLUDED.degree_level, documents.degree_level),
                language = EXCLUDED.language,
                char_count = EXCLUDED.char_count,
                status = 'uploaded',
                source_type = EXCLUDED.source_type,
                original_file_path = COALESCE(EXCLUDED.original_file_path, documents.original_file_path),
                cleaned_text_path = COALESCE(EXCLUDED.cleaned_text_path, documents.cleaned_text_path),
                updated_at = now()
            RETURNING *
        """
        return self._fetchone(
            query,
            (
                title,
                filename,
                subject,
                degree_level,
                language,
                doc_hash,
                char_count,
                source_type,
                original_file_path,
                cleaned_text_path,
            ),
        )

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        return self._fetchone("SELECT * FROM documents WHERE id = %s", (document_id,))

    def get_document_by_hash(self, doc_hash: str) -> dict[str, Any] | None:
        return self._fetchone(
            "SELECT * FROM documents WHERE doc_hash = %s", (doc_hash,)
        )

    def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        display_name: str,
        email_verified_at: datetime | None,
    ) -> dict[str, Any]:
        return self._fetchone(
            """
            INSERT INTO app_users (
                email,
                password_hash,
                display_name,
                status,
                email_verified_at,
                credits_balance
            )
            VALUES (%s, %s, %s, 'active', %s, 0)
            RETURNING *
            """,
            (email, password_hash, display_name, email_verified_at),
        )

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self._fetchone("SELECT * FROM app_users WHERE id = %s", (user_id,))

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return self._fetchone("SELECT * FROM app_users WHERE email = %s", (email,))

    def update_user_verification_email_sent_at(
        self, user_id: str, sent_at: datetime
    ) -> None:
        self._execute(
            """
            UPDATE app_users
            SET verification_email_sent_at = %s, updated_at = now()
            WHERE id = %s
            """,
            (sent_at, user_id),
        )

    def create_email_verification_token(
        self, *, user_id: str, token_hash: str, expires_at: datetime
    ) -> dict[str, Any]:
        return self._fetchone(
            """
            INSERT INTO user_email_verification_tokens (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
            RETURNING *
            """,
            (user_id, token_hash, expires_at),
        )

    def revoke_active_email_verification_tokens(self, user_id: str) -> None:
        self._execute(
            """
            UPDATE user_email_verification_tokens
            SET revoked_at = now()
            WHERE user_id = %s AND used_at IS NULL AND revoked_at IS NULL
            """,
            (user_id,),
        )

    def get_email_verification_token(
        self, token_hash: str
    ) -> dict[str, Any] | None:
        return self._fetchone(
            """
            SELECT
                tokens.*,
                users.email,
                users.display_name,
                users.status,
                users.email_verified_at,
                users.credits_balance,
                users.created_at AS user_created_at
            FROM user_email_verification_tokens AS tokens
            JOIN app_users AS users ON users.id = tokens.user_id
            WHERE tokens.token_hash = %s
            LIMIT 1
            """,
            (token_hash,),
        )

    def mark_email_verification_token_used(
        self, token_hash: str, used_at: datetime
    ) -> None:
        self._execute(
            """
            UPDATE user_email_verification_tokens
            SET used_at = %s
            WHERE token_hash = %s AND used_at IS NULL
            """,
            (used_at, token_hash),
        )

    def mark_user_email_verified(
        self, user_id: str, verified_at: datetime
    ) -> dict[str, Any] | None:
        return self._fetchone(
            """
            UPDATE app_users
            SET email_verified_at = COALESCE(email_verified_at, %s), updated_at = now()
            WHERE id = %s
            RETURNING *
            """,
            (verified_at, user_id),
        )

    def delete_user(self, user_id: str) -> bool:
        """删除用户及其关联数据（GDPR/个人信息保护法删除权）。"""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                # 外键约束会自动级联删除 billing_orders, credit_ledger,
                # user_document_access, user_sessions 等
                cur.execute(
                    "DELETE FROM app_users WHERE id = %s RETURNING id", (user_id,)
                )
                row = cur.fetchone()
            conn.commit()
        return row is not None

    def export_user_data(self, user_id: str) -> dict[str, Any]:
        """导出用户全部个人数据（GDPR/个人信息保护法查阅权）。"""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, email, display_name, status, credits_balance, created_at, updated_at FROM app_users WHERE id = %s",
                    (user_id,),
                )
                user = cur.fetchone()

                cur.execute(
                    "SELECT id, task_type, status, progress, created_at, finished_at FROM analysis_tasks WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,),
                )
                tasks = cur.fetchall()

                cur.execute(
                    "SELECT id, order_no, package_code, status, amount_cents, credits, created_at, paid_at FROM billing_orders WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,),
                )
                orders = cur.fetchall()

                cur.execute(
                    "SELECT id, change_amount, balance_after, source_type, note, created_at FROM credit_ledger WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,),
                )
                ledger = cur.fetchall()

                cur.execute(
                    "SELECT document_id, created_at FROM user_document_access WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,),
                )
                accesses = cur.fetchall()

                try:
                    cur.execute(
                        "SELECT id, action, resource_type, resource_id, created_at FROM audit_logs WHERE user_id = %s ORDER BY created_at DESC",
                        (user_id,),
                    )
                    audits = cur.fetchall()
                except Exception:
                    audits = []

        return {
            "user": user,
            "tasks": tasks or [],
            "orders": orders or [],
            "credit_ledger": ledger or [],
            "document_accesses": accesses or [],
            "audit_logs": audits or [],
            "exported_at": datetime.now(UTC).isoformat(),
        }

    def create_user_session(
        self, *, user_id: str, token_hash: str, expires_at: Any
    ) -> dict[str, Any]:
        return self._fetchone(
            """
            INSERT INTO user_sessions (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
            RETURNING *
            """,
            (user_id, token_hash, expires_at),
        )

    def get_user_session(self, token_hash: str) -> dict[str, Any] | None:
        return self._fetchone(
            """
            SELECT
                sessions.*,
                users.email,
                users.display_name,
                users.status,
                users.email_verified_at,
                users.credits_balance,
                users.created_at AS user_created_at
            FROM user_sessions AS sessions
            JOIN app_users AS users ON users.id = sessions.user_id
            WHERE sessions.token_hash = %s
              AND sessions.revoked_at IS NULL
              AND sessions.expires_at > now()
            LIMIT 1
            """,
            (token_hash,),
        )

    def touch_user_session(self, token_hash: str) -> None:
        self._execute(
            "UPDATE user_sessions SET last_seen_at = now() WHERE token_hash = %s AND revoked_at IS NULL",
            (token_hash,),
        )

    def revoke_user_session(self, token_hash: str) -> None:
        self._execute(
            "UPDATE user_sessions SET revoked_at = now() WHERE token_hash = %s AND revoked_at IS NULL",
            (token_hash,),
        )

    def revoke_all_user_sessions(self, user_id: str) -> None:
        self._execute(
            "UPDATE user_sessions SET revoked_at = now() WHERE user_id = %s AND revoked_at IS NULL",
            (user_id,),
        )

    def change_user_credits(
        self,
        *,
        user_id: str,
        delta: int,
        source_type: str,
        source_id: str | None,
        note: str | None,
    ) -> dict[str, Any]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM app_users WHERE id = %s FOR UPDATE", (user_id,)
                )
                user = cur.fetchone()
                if user is None:
                    raise ValueError("user not found")
                current_balance = int(user.get("credits_balance", 0))
                new_balance = current_balance + int(delta)
                if new_balance < 0:
                    raise ValueError("credits not enough")
                cur.execute(
                    "UPDATE app_users SET credits_balance = %s, updated_at = now() WHERE id = %s RETURNING *",
                    (new_balance, user_id),
                )
                updated_user = cur.fetchone()
                cur.execute(
                    """
                    INSERT INTO credit_ledger (user_id, change_amount, balance_after, source_type, source_id, note)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (user_id, delta, new_balance, source_type, source_id, note),
                )
                ledger = cur.fetchone()
            conn.commit()
        return {
            "user": _normalize_row(updated_user),
            "ledger": _normalize_row(ledger),
            "balance_after": new_balance,
        }

    def list_credit_ledger(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT *
            FROM credit_ledger
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )

    def create_billing_order(
        self,
        *,
        user_id: str,
        order_no: str,
        package_code: str,
        credits: int,
        amount_cents: int,
        status: str,
        provider: str,
        paid_at: Any,
        payment_payload: dict[str, Any] | None,
        provider_trade_no: str | None,
        notified_at: Any,
    ) -> dict[str, Any]:
        return self._fetchone(
            """
            INSERT INTO billing_orders (
                user_id,
                order_no,
                package_code,
                credits,
                amount_cents,
                status,
                provider,
                paid_at,
                payment_payload,
                provider_trade_no,
                notified_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                user_id,
                order_no,
                package_code,
                credits,
                amount_cents,
                status,
                provider,
                paid_at,
                Jsonb(jsonable_encoder(payment_payload or {})),
                provider_trade_no,
                notified_at,
            ),
        )

    def get_billing_order(self, order_no: str) -> dict[str, Any] | None:
        return self._fetchone(
            "SELECT * FROM billing_orders WHERE order_no = %s", (order_no,)
        )

    def get_user_billing_order(
        self, user_id: str, order_no: str
    ) -> dict[str, Any] | None:
        return self._fetchone(
            "SELECT * FROM billing_orders WHERE user_id = %s AND order_no = %s",
            (user_id, order_no),
        )

    def list_user_orders(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT *
            FROM billing_orders
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )

    def pay_billing_order_if_unpaid(
        self,
        *,
        order_no: str,
        provider: str,
        note: str | None,
        provider_trade_no: str | None = None,
        payment_payload: dict[str, Any] | None = None,
        notified_at: Any = None,
    ) -> dict[str, Any]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM billing_orders WHERE order_no = %s FOR UPDATE",
                    (order_no,),
                )
                order = cur.fetchone()
                if order is None:
                    raise ValueError("order not found")

                order_status = str(order.get("status") or "")
                user_id = str(order["user_id"])

                if order_status == "paid":
                    cur.execute(
                        "SELECT credits_balance FROM app_users WHERE id = %s",
                        (user_id,),
                    )
                    user_row = cur.fetchone()
                    balance_after = int((user_row or {}).get("credits_balance", 0))
                    conn.commit()
                    return {
                        "order": _normalize_row(order),
                        "balance_after": balance_after,
                        "credited": False,
                    }

                if order_status not in {"pending", "created"}:
                    raise ValueError(f"order status {order_status} cannot be paid")

                merged_payload = _merge_json_payload(
                    order.get("payment_payload"), payment_payload
                )

                cur.execute(
                    """
                    UPDATE billing_orders
                    SET status = 'paid',
                        provider = %s,
                        paid_at = COALESCE(paid_at, now()),
                        payment_payload = %s,
                        provider_trade_no = COALESCE(%s, provider_trade_no),
                        notified_at = COALESCE(%s, notified_at)
                    WHERE id = %s
                    RETURNING *
                    """,
                    (
                        provider,
                        Jsonb(jsonable_encoder(merged_payload)),
                        provider_trade_no,
                        notified_at,
                        order["id"],
                    ),
                )
                paid_order = cur.fetchone()

                cur.execute(
                    "SELECT * FROM app_users WHERE id = %s FOR UPDATE", (user_id,)
                )
                user = cur.fetchone()
                if user is None:
                    raise ValueError("user not found")

                current_balance = int(user.get("credits_balance", 0))
                new_balance = current_balance + int(order["credits"])
                cur.execute(
                    "UPDATE app_users SET credits_balance = %s, updated_at = now() WHERE id = %s",
                    (new_balance, user_id),
                )
                cur.execute(
                    """
                    INSERT INTO credit_ledger (user_id, change_amount, balance_after, source_type, source_id, note)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        int(order["credits"]),
                        new_balance,
                        "order_purchase",
                        order["id"],
                        note,
                    ),
                )
            conn.commit()

        return {
            "order": _normalize_row(paid_order),
            "balance_after": new_balance,
            "credited": True,
        }

    def grant_document_access(self, *, user_id: str, document_id: str) -> None:
        self._execute(
            """
            INSERT INTO user_document_access (user_id, document_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id, document_id) DO NOTHING
            """,
            (user_id, document_id),
        )

    def can_user_access_document(
        self, *, user_id: str | None, document_id: str
    ) -> bool:
        row = self._fetchone(
            """
            SELECT
                COUNT(*) AS total_rows,
                SUM(CASE WHEN user_id = %s THEN 1 ELSE 0 END) AS matched_rows
            FROM user_document_access
            WHERE document_id = %s
            """,
            (user_id, document_id),
        )
        total_rows = int((row or {}).get("total_rows", 0))
        matched_rows = int((row or {}).get("matched_rows", 0) or 0)
        if total_rows == 0:
            return True
        if user_id is None:
            return False
        return matched_rows > 0

    def create_analysis_run(
        self,
        *,
        document_id: str,
        run_type: str = "full_analysis",
        provider: str = "local",
        provider_version: str | None = None,
        mode: str = "estimate",
    ) -> dict[str, Any]:
        query = """
            INSERT INTO analysis_runs (document_id, run_type, provider, provider_version, status, mode)
            VALUES (%s, %s, %s, %s, 'queued', %s)
            RETURNING *
        """
        return self._fetchone(
            query, (document_id, run_type, provider, provider_version, mode)
        )

    def update_run_mode(self, run_id: str, mode: str) -> dict[str, Any] | None:
        return self._fetchone(
            """
            UPDATE analysis_runs SET mode = %s WHERE id = %s RETURNING *
            """,
            (mode, run_id),
        )

    def mark_document_status(
        self, document_id: str, status: str, *, section_count: int | None = None
    ) -> None:
        if section_count is None:
            self._execute(
                "UPDATE documents SET status = %s, updated_at = now() WHERE id = %s",
                (status, document_id),
            )
            return
        self._execute(
            "UPDATE documents SET status = %s, section_count = %s, updated_at = now() WHERE id = %s",
            (status, section_count, document_id),
        )

    def mark_run_processing(self, run_id: str) -> None:
        self._execute(
            "UPDATE analysis_runs SET status = 'processing', started_at = now(), error_message = NULL WHERE id = %s",
            (run_id,),
        )

    def mark_run_completed(self, run_id: str) -> None:
        self._execute(
            "UPDATE analysis_runs SET status = 'completed', finished_at = now() WHERE id = %s",
            (run_id,),
        )

    def mark_run_failed(self, run_id: str, error_message: str) -> None:
        self._execute(
            "UPDATE analysis_runs SET status = 'failed', finished_at = now(), error_message = %s WHERE id = %s",
            (error_message[:2000], run_id),
        )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        query = """
            SELECT
                runs.*,
                documents.title,
                documents.filename,
                documents.subject,
                documents.degree_level,
                documents.status AS document_status
            FROM analysis_runs AS runs
            JOIN documents ON documents.id = runs.document_id
            WHERE runs.id = %s
        """
        return self._fetchone(query, (run_id,))

    def list_completed_runs(
        self, document_id: str, limit: int = 1
    ) -> list[dict[str, Any]]:
        """返回指定文档已完成的分析记录（最新在前）。"""
        query = """
            SELECT
                runs.*,
                documents.title,
                documents.filename,
                documents.subject,
                documents.degree_level,
                documents.status AS document_status
            FROM analysis_runs AS runs
            JOIN documents ON documents.id = runs.document_id
            WHERE runs.document_id = %s AND runs.status = 'completed'
            ORDER BY runs.finished_at DESC
            LIMIT %s
        """
        return self._fetchall(query, (document_id, limit))

    def list_processing_runs(
        self, document_id: str, limit: int = 1
    ) -> list[dict[str, Any]]:
        """返回指定文档正在处理中的分析记录（最新在前）。"""
        query = """
            SELECT
                runs.*,
                documents.title,
                documents.filename,
                documents.subject,
                documents.degree_level,
                documents.status AS document_status
            FROM analysis_runs AS runs
            JOIN documents ON documents.id = runs.document_id
            WHERE runs.document_id = %s AND runs.status = 'processing'
            ORDER BY runs.created_at DESC
            LIMIT %s
        """
        return self._fetchall(query, (document_id, limit))

    def create_analysis_task(
        self, *, user_id: str | None, document_id: str, task_type: str = "analysis"
    ) -> dict[str, Any]:
        return self._fetchone(
            """
            INSERT INTO analysis_tasks (user_id, document_id, task_type, status, progress, result_json)
            VALUES (%s, %s, %s, 'queued', 0, '{}'::jsonb)
            RETURNING *
            """,
            (user_id, document_id, task_type),
        )

    def list_active_analysis_tasks(
        self, document_id: str, limit: int = 1
    ) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT tasks.*, documents.title, documents.filename
            FROM analysis_tasks AS tasks
            JOIN documents ON documents.id = tasks.document_id
            WHERE tasks.document_id = %s
              AND tasks.status IN ('queued', 'processing')
            ORDER BY tasks.created_at DESC
            LIMIT %s
            """,
            (document_id, limit),
        )

    def recover_stale_document_tasks(
        self, document_id: str, max_age_minutes: int = 15
    ) -> int:
        query = """
            UPDATE analysis_tasks
            SET status = 'failed',
                progress = 100,
                finished_at = now(),
                error_message = COALESCE(
                    error_message,
                    '服务恢复：检测到残留 queued/processing 任务，已自动释放'
                )
            WHERE document_id = %s
              AND status IN ('queued', 'processing')
              AND created_at < now() - make_interval(mins => %s)
        """
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (document_id, max_age_minutes))
                count = cur.rowcount
            conn.commit()
        return count

    def mark_analysis_task_processing(
        self, task_id: str, *, progress: int = 35
    ) -> None:
        self._execute(
            """
            UPDATE analysis_tasks
            SET status = 'processing', progress = %s, started_at = COALESCE(started_at, now()), error_message = NULL
            WHERE id = %s
            """,
            (progress, task_id),
        )

    def mark_analysis_task_completed(
        self, task_id: str, *, run_id: str, result_json: dict[str, Any]
    ) -> None:
        self._execute(
            """
            UPDATE analysis_tasks
            SET status = 'completed',
                progress = 100,
                run_id = %s,
                finished_at = now(),
                result_json = %s
            WHERE id = %s
            """,
            (run_id, Jsonb(jsonable_encoder(result_json)), task_id),
        )

    def mark_analysis_task_failed(self, task_id: str, *, error_message: str) -> None:
        self._execute(
            """
            UPDATE analysis_tasks
            SET status = 'failed',
                progress = 100,
                finished_at = now(),
                error_message = %s
            WHERE id = %s
            """,
            (error_message[:2000], task_id),
        )

    def get_analysis_task(self, task_id: str) -> dict[str, Any] | None:
        return self._fetchone(
            """
            SELECT tasks.*, documents.title, documents.filename
            FROM analysis_tasks AS tasks
            JOIN documents ON documents.id = tasks.document_id
            WHERE tasks.id = %s
            """,
            (task_id,),
        )

    def recover_stale_tasks(self, max_age_minutes: int = 30) -> int:
        """将超时卡在 processing 的任务标记为 failed。"""
        query = """
            UPDATE analysis_tasks
            SET status = 'failed',
                progress = 100,
                finished_at = now(),
                error_message = '服务重启恢复：任务超时未完成'
            WHERE status = 'processing'
              AND started_at < now() - interval '%s minutes'
        """
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (max_age_minutes,))
                count = cur.rowcount
            conn.commit()
        return count

    def recover_orphan_processing_runs(
        self, document_id: str, max_age_minutes: int = 15
    ) -> int:
        query = """
            UPDATE analysis_runs AS runs
            SET status = 'failed',
                finished_at = now(),
                error_message = '服务恢复：检测到残留 processing run，已自动释放'
            WHERE runs.document_id = %s
              AND runs.status = 'processing'
              AND COALESCE(runs.started_at, runs.created_at) < now() - make_interval(mins => %s)
              AND NOT EXISTS (
                    SELECT 1
                    FROM analysis_tasks AS tasks
                    WHERE tasks.document_id = runs.document_id
                      AND tasks.status IN ('queued', 'processing')
              )
        """
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (document_id, max_age_minutes))
                count = cur.rowcount
            conn.commit()
        return count

    def get_analysis_task_summary(self) -> dict[str, Any]:
        """Return aggregate task health for admin operations dashboards."""
        query = """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE status = 'queued') AS queued,
                COUNT(*) FILTER (WHERE status = 'processing') AS processing,
                COUNT(*) FILTER (WHERE status = 'completed') AS completed,
                COUNT(*) FILTER (WHERE status = 'failed') AS failed,
                MIN(created_at) FILTER (WHERE status = 'queued') AS oldest_queued_at,
                MAX(finished_at) FILTER (WHERE status = 'failed') AS latest_failed_at,
                AVG(EXTRACT(EPOCH FROM (finished_at - started_at)))
                    FILTER (WHERE status = 'completed' AND started_at IS NOT NULL AND finished_at IS NOT NULL)
                    AS avg_completed_seconds
            FROM analysis_tasks
        """
        summary = self._fetchone(query, ()) or {}
        latest_failed = self._fetchone(
            """
            SELECT id, document_id, error_message, finished_at
            FROM analysis_tasks
            WHERE status = 'failed'
            ORDER BY finished_at DESC NULLS LAST, created_at DESC
            LIMIT 1
            """,
            (),
        )
        return {
            "total": int(summary.get("total") or 0),
            "queued": int(summary.get("queued") or 0),
            "processing": int(summary.get("processing") or 0),
            "completed": int(summary.get("completed") or 0),
            "failed": int(summary.get("failed") or 0),
            "oldest_queued_at": summary.get("oldest_queued_at"),
            "latest_failed_at": summary.get("latest_failed_at"),
            "avg_completed_seconds": summary.get("avg_completed_seconds"),
            "latest_failed_task": latest_failed,
        }

    def list_user_analysis_tasks(
        self, user_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT tasks.*, documents.title, documents.filename
            FROM analysis_tasks AS tasks
            JOIN documents ON documents.id = tasks.document_id
            WHERE tasks.user_id = %s
            ORDER BY tasks.created_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )

    def list_feedback_records(self) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT
                feedback.*,
                documents.subject,
                documents.degree_level,
                COALESCE(documents.subject, 'general') || ':' || COALESCE(documents.degree_level, 'general') AS scene_key
            FROM cnki_feedback AS feedback
            JOIN documents ON documents.id = feedback.document_id
            ORDER BY feedback.created_at DESC
            """,
            (),
        )

    def count_feedback_records(self) -> int:
        row = self._fetchone("SELECT COUNT(*) AS total FROM cnki_feedback", ())
        return int((row or {}).get("total", 0))

    def list_cnki_feedback_for_document(
        self, document_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT *
            FROM cnki_feedback
            WHERE document_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (document_id, limit),
        )

    def list_document_sections(self, document_id: str) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT *
            FROM document_sections
            WHERE document_id = %s
            ORDER BY section_index
            """,
            (document_id,),
        )

    def delete_document_sections(self, document_id: str) -> None:
        self._execute(
            "DELETE FROM document_sections WHERE document_id = %s",
            (document_id,),
        )

    def insert_document_sections(
        self, document_id: str, sections: Sequence[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not sections:
            return []
        query = """
            INSERT INTO document_sections (
                document_id,
                section_index,
                paragraph_index,
                section_type,
                section_title,
                text_preview,
                content,
                char_count,
                embedding
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
            RETURNING *
        """
        params_list = [
            (
                document_id,
                section["section_index"],
                section.get("paragraph_index"),
                section.get("section_type"),
                _strip_nul_bytes(section.get("section_title")),
                _strip_nul_bytes(section.get("text_preview")),
                _strip_nul_bytes(section["content"]),
                section["char_count"],
                section.get("embedding"),
            )
            for section in sections
        ]
        created: list[dict[str, Any]] = []
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(query, params_list, returning=True)
                # executemany with returning=True: fetch all result sets
                while True:
                    row = cur.fetchone()
                    if row is not None:
                        created.append(row)
                    if not cur.nextset():
                        break
            conn.commit()
        return created

    def find_similar_sections(
        self,
        embedding_str: str,
        exclude_document_id: str,
        limit: int = 5,
        distance_threshold: float = 0.35,
    ) -> list[dict[str, Any]]:
        """用 pgvector 余弦距离检索其他文档中的相似段落。

        返回的每条记录包含 distance 字段（越小越相似，0=完全相同）。
        """
        query = """
            SELECT
                ds.*,
                d.title AS document_title,
                d.filename AS document_filename,
                (ds.embedding <=> %s::vector) AS distance
            FROM document_sections ds
            JOIN documents d ON d.id = ds.document_id
            WHERE ds.document_id != %s
              AND ds.embedding IS NOT NULL
              AND (ds.embedding <=> %s::vector) < %s
            ORDER BY ds.embedding <=> %s::vector
            LIMIT %s
        """
        return self._fetchall(
            query,
            (
                embedding_str,
                exclude_document_id,
                embedding_str,
                distance_threshold,
                embedding_str,
                limit,
            ),
        )

    def insert_section_scores(
        self, run_id: str, scores: Sequence[dict[str, Any]]
    ) -> None:
        if not scores:
            return
        query = """
            INSERT INTO section_scores (
                run_id,
                document_section_id,
                score_type,
                raw_score,
                normalized_score,
                risk_level,
                reasons,
                signals
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (run_id, document_section_id, score_type) DO UPDATE
            SET
                raw_score = EXCLUDED.raw_score,
                normalized_score = EXCLUDED.normalized_score,
                risk_level = EXCLUDED.risk_level,
                reasons = EXCLUDED.reasons,
                signals = EXCLUDED.signals
        """
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                for score in scores:
                    cur.execute(
                        query,
                        (
                            run_id,
                            score["document_section_id"],
                            score["score_type"],
                            score.get("raw_score"),
                            score.get("normalized_score"),
                            score.get("risk_level"),
                            Jsonb(_strip_nul_bytes(score.get("reasons", []))),
                            Jsonb(_strip_nul_bytes(score.get("signals", []))),
                        ),
                    )
            conn.commit()

    def list_section_scores(self, run_id: str) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT
                ss.run_id,
                ss.score_type,
                ss.raw_score,
                ss.normalized_score,
                ss.risk_level,
                ss.reasons,
                ds.section_index
            FROM section_scores ss
            JOIN document_sections ds ON ds.id = ss.document_section_id
            WHERE ss.run_id = %s
            """,
            (run_id,),
        )

    def insert_similarity_matches(
        self, run_id: str, matches: Sequence[dict[str, Any]]
    ) -> None:
        if not matches:
            return
        query = """
            INSERT INTO similarity_matches (
                run_id,
                document_section_id,
                matched_source,
                matched_title,
                matched_snippet,
                similarity_score,
                overlap_chars,
                match_type,
                source_url
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                for match in matches:
                    cur.execute(
                        query,
                        (
                            run_id,
                            match["document_section_id"],
                            _strip_nul_bytes(match.get("matched_source")),
                            _strip_nul_bytes(match.get("matched_title")),
                            _strip_nul_bytes(match.get("matched_snippet")),
                            match["similarity_score"],
                            match.get("overlap_chars", 0),
                            match.get("match_type"),
                            _strip_nul_bytes(match.get("source_url")),
                        ),
                    )
            conn.commit()

    def insert_provider_payload(
        self, run_id: str, provider: str, payload_type: str, payload: dict[str, Any]
    ) -> None:
        self._execute(
            """
            INSERT INTO provider_payloads (run_id, provider, payload_type, payload)
            VALUES (%s, %s, %s, %s)
            """,
            (
                run_id,
                provider,
                payload_type,
                Jsonb(_strip_nul_bytes(jsonable_encoder(payload))),
            ),
        )

    def insert_provider_payload_row(
        self,
        run_id: str,
        provider: str,
        payload_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self._fetchone(
            """
            INSERT INTO provider_payloads (run_id, provider, payload_type, payload)
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (
                run_id,
                provider,
                payload_type,
                Jsonb(_strip_nul_bytes(jsonable_encoder(payload))),
            ),
        )

    def list_provider_payloads(self, run_id: str) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT *
            FROM provider_payloads
            WHERE run_id = %s
            ORDER BY created_at ASC
            """,
            (run_id,),
        )

    def insert_proxy_prediction(
        self,
        *,
        document_id: str,
        run_id: str,
        model_version: str,
        scene_key: str | None,
        predicted_cnki_dup: float,
        predicted_cnki_dup_low: float,
        predicted_cnki_dup_high: float,
        predicted_cnki_aigc: float,
        predicted_cnki_aigc_low: float,
        predicted_cnki_aigc_high: float,
        confidence: float,
        summary: dict[str, Any],
    ) -> dict[str, Any]:
        query = """
            INSERT INTO proxy_predictions (
                document_id,
                run_id,
                model_version,
                scene_key,
                predicted_cnki_dup,
                predicted_cnki_dup_low,
                predicted_cnki_dup_high,
                predicted_cnki_aigc,
                predicted_cnki_aigc_low,
                predicted_cnki_aigc_high,
                confidence,
                summary
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        return self._fetchone(
            query,
            (
                document_id,
                run_id,
                model_version,
                scene_key,
                predicted_cnki_dup,
                predicted_cnki_dup_low,
                predicted_cnki_dup_high,
                predicted_cnki_aigc,
                predicted_cnki_aigc_low,
                predicted_cnki_aigc_high,
                confidence,
                Jsonb(_strip_nul_bytes(jsonable_encoder(summary))),
            ),
        )

    def save_report_snapshot(
        self, *, document_id: str, run_id: str, report_json: dict[str, Any]
    ) -> dict[str, Any]:
        query = """
            INSERT INTO report_snapshots (document_id, run_id, report_json)
            VALUES (%s, %s, %s)
            RETURNING *
        """
        return self._fetchone(
            query,
            (
                document_id,
                run_id,
                Jsonb(_strip_nul_bytes(jsonable_encoder(report_json))),
            ),
        )

    def register_model(
        self,
        *,
        model_name: str,
        model_type: str,
        version: str,
        scene_key: str | None,
        metrics: dict[str, Any],
        artifact_path: str,
        activate: bool,
    ) -> dict[str, Any]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                if activate:
                    cur.execute(
                        """
                        UPDATE model_registry
                        SET is_active = false
                        WHERE model_type = %s
                          AND COALESCE(scene_key, '') = COALESCE(%s, '')
                        """,
                        (model_type, scene_key),
                    )
                cur.execute(
                    """
                    INSERT INTO model_registry (
                        model_name,
                        model_type,
                        version,
                        scene_key,
                        is_active,
                        metrics,
                        artifact_path
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        model_name,
                        model_type,
                        version,
                        scene_key,
                        activate,
                        Jsonb(jsonable_encoder(metrics)),
                        artifact_path,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return _normalize_row(row)

    def get_active_model(
        self, model_type: str, scene_key: str | None
    ) -> dict[str, Any] | None:
        exact = self._fetchone(
            """
            SELECT *
            FROM model_registry
            WHERE model_type = %s
              AND is_active = true
              AND scene_key = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (model_type, scene_key),
        )
        if exact is not None:
            return exact
        return self._fetchone(
            """
            SELECT *
            FROM model_registry
            WHERE model_type = %s
              AND is_active = true
              AND scene_key IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (model_type,),
        )

    def list_active_models(self) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT *
            FROM model_registry
            WHERE is_active = true
            ORDER BY model_type ASC, created_at DESC
            """,
            (),
        )

    def list_recent_models(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT *
            FROM model_registry
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )

    def get_report_snapshot(self, run_id: str) -> dict[str, Any] | None:
        row = self._fetchone(
            """
            SELECT *
            FROM report_snapshots
            WHERE run_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (run_id,),
        )
        return row

    def get_proxy_prediction(self, run_id: str) -> dict[str, Any] | None:
        return self._fetchone(
            """
            SELECT *
            FROM proxy_predictions
            WHERE run_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (run_id,),
        )

    def create_cnki_feedback(
        self,
        *,
        document_id: str,
        predicted_run_id: str | None,
        cnki_dup_percent: float | None,
        cnki_aigc_percent: float | None,
        report_date: date | None,
        evidence_path: str | None,
        notes: str | None,
        details: dict[str, Any] | None = None,
        verified: bool = False,
    ) -> dict[str, Any]:
        query = """
            INSERT INTO cnki_feedback (
                document_id,
                predicted_run_id,
                cnki_dup_percent,
                cnki_aigc_percent,
                report_date,
                evidence_path,
                notes,
                details,
                verified
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        import json

        return self._fetchone(
            query,
            (
                document_id,
                predicted_run_id,
                cnki_dup_percent,
                cnki_aigc_percent,
                report_date,
                evidence_path,
                notes,
                json.dumps(_strip_nul_bytes(details)) if details else "{}",
                verified,
            ),
        )

    def _fetchone(self, query: str, params: Sequence[Any]) -> dict[str, Any] | None:
        sanitized_params = _strip_nul_bytes(tuple(params))
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, sanitized_params)
                row = cur.fetchone()
            conn.commit()
        return _normalize_row(row)

    def _fetchall(self, query: str, params: Sequence[Any]) -> list[dict[str, Any]]:
        sanitized_params = _strip_nul_bytes(tuple(params))
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, sanitized_params)
                rows = cur.fetchall()
            conn.commit()
        return [_normalize_row(row) for row in rows]

    def _execute(self, query: str, params: Sequence[Any]) -> None:
        sanitized_params = _strip_nul_bytes(tuple(params))
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, sanitized_params)
            conn.commit()

    # ------------------------------------------------------------------
    # Document Blocks
    # ------------------------------------------------------------------

    def insert_document_blocks(
        self, document_id: str, blocks: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not blocks:
            return []
        query = """
            INSERT INTO document_blocks (
                document_id,
                block_id,
                block_type,
                text,
                html,
                source_type,
                source_map,
                section_index,
                paragraph_index,
                section_title,
                section_type,
                char_count,
                display_order
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        params_list = [
            (
                document_id,
                b["block_id"],
                b["block_type"],
                _strip_nul_bytes(b["text"]),
                _strip_nul_bytes(b.get("html")),
                b["source_type"],
                Jsonb(b.get("source_map") or {}),
                b.get("section_index"),
                b.get("paragraph_index"),
                _strip_nul_bytes(b.get("section_title")),
                b.get("section_type"),
                b.get("char_count", 0),
                b["display_order"],
            )
            for b in blocks
        ]
        created: list[dict[str, Any]] = []
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(query, params_list, returning=True)
                while True:
                    row = cur.fetchone()
                    if row is not None:
                        created.append(row)
                    if not cur.nextset():
                        break
            conn.commit()
        return created

    def list_document_blocks(self, document_id: str) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT *
            FROM document_blocks
            WHERE document_id = %s
            ORDER BY display_order
            """,
            (document_id,),
        )

    def get_document_block(self, document_id: str, block_id: str) -> dict[str, Any] | None:
        return self._fetchone(
            """
            SELECT * FROM document_blocks
            WHERE document_id = %s AND block_id = %s
            """,
            (document_id, block_id),
        )

    def update_block_risk_score(
        self, document_id: str, block_id: str, risk_score: float
    ) -> dict[str, Any] | None:
        return self._fetchone(
            """
            UPDATE document_blocks
            SET risk_score = %s
            WHERE document_id = %s AND block_id = %s
            RETURNING *
            """,
            (risk_score, document_id, block_id),
        )

    def update_block_internal_risk(
        self, document_id: str, block_id: str, internal_risk: dict[str, Any]
    ) -> dict[str, Any] | None:
        return self._fetchone(
            """
            UPDATE document_blocks
            SET internal_risk = %s
            WHERE document_id = %s AND block_id = %s
            RETURNING *
            """,
            (Jsonb(internal_risk), document_id, block_id),
        )

    # ------------------------------------------------------------------
    # Document Patches
    # ------------------------------------------------------------------

    def insert_document_patch(
        self,
        document_id: str,
        run_id: str | None,
        block_id: str,
        old_text: str,
        new_text: str,
        source_map: dict[str, Any] | None = None,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        return self._fetchone(
            """
            INSERT INTO document_patches (
                document_id, run_id, block_id, old_text, new_text, source_map, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                document_id,
                run_id,
                block_id,
                old_text,
                new_text,
                Jsonb(source_map or {}),
                created_by,
            ),
        )

    def list_document_patches(
        self, document_id: str, run_id: str | None = None
    ) -> list[dict[str, Any]]:
        if run_id:
            return self._fetchall(
                """
                SELECT * FROM document_patches
                WHERE document_id = %s AND run_id = %s
                ORDER BY created_at
                """,
                (document_id, run_id),
            )
        return self._fetchall(
            """
            SELECT * FROM document_patches
            WHERE document_id = %s
            ORDER BY created_at
            """,
            (document_id,),
        )

    def get_latest_patch_for_block(
        self, document_id: str, block_id: str
    ) -> dict[str, Any] | None:
        return self._fetchone(
            """
            SELECT * FROM document_patches
            WHERE document_id = %s AND block_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (document_id, block_id),
        )

    def list_latest_patches_by_run(
        self, document_id: str, run_id: str
    ) -> list[dict[str, Any]]:
        """返回每个 block 在该 run 下的最新 patch（去重）。"""
        return self._fetchall(
            """
            SELECT DISTINCT ON (block_id) *
            FROM document_patches
            WHERE document_id = %s AND run_id = %s
            ORDER BY block_id, created_at DESC
            """,
            (document_id, run_id),
        )

    # ------------------------------------------------------------------
    # CNKI Reports
    # ------------------------------------------------------------------

    def insert_cnki_report(
        self,
        *,
        document_id: str,
        run_id: str | None = None,
        report_type: str,
        filename: str | None = None,
        raw_format: str | None = None,
        total_copy_ratio: float | None = None,
        aigc_ratio: float | None = None,
        generated_at: str | None = None,
        raw_data: dict[str, Any] | None = None,
        status: str = "parsed",
    ) -> dict[str, Any]:
        return self._fetchone(
            """
            INSERT INTO cnki_reports (
                document_id, run_id, report_type, filename, raw_format,
                total_copy_ratio, aigc_ratio, generated_at, raw_data, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                document_id,
                run_id,
                report_type,
                filename,
                raw_format,
                total_copy_ratio,
                aigc_ratio,
                generated_at,
                Jsonb(raw_data or {}),
                status,
            ),
        )

    def get_cnki_report(self, report_id: str) -> dict[str, Any] | None:
        return self._fetchone(
            "SELECT * FROM cnki_reports WHERE id = %s",
            (report_id,),
        )

    def list_cnki_reports_by_document(self, document_id: str) -> list[dict[str, Any]]:
        return self._fetchall(
            "SELECT * FROM cnki_reports WHERE document_id = %s ORDER BY parsed_at DESC",
            (document_id,),
        )

    # ------------------------------------------------------------------
    # CNKI Report Spans
    # ------------------------------------------------------------------

    def insert_cnki_report_spans(
        self, report_id: str, spans: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not spans:
            return []
        query = """
            INSERT INTO cnki_report_spans (
                report_id, span_id, text, risk_type, risk_level,
                similarity, aigc_score, matched_source, page_number, raw_meta
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        results: list[dict[str, Any]] = []
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                for span in spans:
                    cur.execute(
                        query,
                        (
                            report_id,
                            span["span_id"],
                            span["text"],
                            span["risk_type"],
                            span["risk_level"],
                            span.get("similarity"),
                            span.get("aigc_score"),
                            span.get("matched_source"),
                            span.get("page_number"),
                            Jsonb(span.get("raw_meta") or {}),
                        ),
                    )
                    row = cur.fetchone()
                    if row:
                        results.append(row)
            conn.commit()
        return results

    def list_cnki_report_spans(self, report_id: str) -> list[dict[str, Any]]:
        return self._fetchall(
            "SELECT * FROM cnki_report_spans WHERE report_id = %s ORDER BY id",
            (report_id,),
        )

    def get_cnki_report_span(
        self, report_id: str, span_id: str
    ) -> dict[str, Any] | None:
        return self._fetchone(
            """
            SELECT *
            FROM cnki_report_spans
            WHERE report_id = %s AND span_id = %s
            """,
            (report_id, span_id),
        )

    def list_unmapped_cnki_report_spans(self, report_id: str) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT s.*
            FROM cnki_report_spans s
            LEFT JOIN block_report_mappings m
              ON m.report_id = s.report_id
             AND m.span_id = s.span_id
            WHERE s.report_id = %s
              AND m.id IS NULL
            ORDER BY s.id
            """,
            (report_id,),
        )

    # ------------------------------------------------------------------
    # Block Report Mappings
    # ------------------------------------------------------------------

    def insert_block_report_mapping(
        self,
        *,
        document_id: str,
        block_id: str,
        span_id: str,
        report_id: str,
        match_method: str,
        match_confidence: float,
        matched_text: str | None = None,
    ) -> dict[str, Any]:
        return self._fetchone(
            """
            INSERT INTO block_report_mappings (
                document_id, block_id, span_id, report_id,
                match_method, match_confidence, matched_text
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (document_id, block_id, span_id) DO UPDATE
            SET match_method = EXCLUDED.match_method,
                match_confidence = EXCLUDED.match_confidence,
                matched_text = EXCLUDED.matched_text,
                report_id = EXCLUDED.report_id
            RETURNING *
            """,
            (
                document_id,
                block_id,
                span_id,
                report_id,
                match_method,
                match_confidence,
                matched_text,
            ),
        )

    def list_block_report_mappings(
        self, document_id: str
    ) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT m.*, s.text as span_text, s.risk_type, s.risk_level,
                   s.similarity, s.aigc_score, s.matched_source
            FROM block_report_mappings m
            JOIN cnki_report_spans s ON s.span_id = m.span_id AND s.report_id = m.report_id
            WHERE m.document_id = %s
            ORDER BY m.created_at DESC
            """,
            (document_id,),
        )

    def delete_block_report_mappings_by_report(self, report_id: str) -> None:
        self._execute(
            "DELETE FROM block_report_mappings WHERE report_id = %s",
            (report_id,),
        )

    # ------------------------------------------------------------------
    # Document Blocks — report risk
    # ------------------------------------------------------------------

    def update_block_report_risk(
        self, document_id: str, block_id: str, report_risk: dict[str, Any]
    ) -> dict[str, Any] | None:
        return self._fetchone(
            """
            UPDATE document_blocks
            SET report_risk = %s
            WHERE document_id = %s AND block_id = %s
            RETURNING *
            """,
            (Jsonb(report_risk), document_id, block_id),
        )

    def clear_block_report_risks(self, document_id: str) -> None:
        self._execute(
            "UPDATE document_blocks SET report_risk = NULL WHERE document_id = %s",
            (document_id,),
        )

    # ------------------------------------------------------------------
    # Run Unlocks
    # ------------------------------------------------------------------

    def create_run_unlock(
        self,
        *,
        user_id: str,
        run_id: str,
        order_no: str,
        package_code: str,
        amount_cents: int,
    ) -> dict[str, Any]:
        return self._fetchone(
            """
            INSERT INTO user_run_unlocks (user_id, run_id, order_no, package_code, amount_cents, status)
            VALUES (%s, %s, %s, %s, %s, 'pending_payment')
            ON CONFLICT (user_id, run_id, package_code) DO UPDATE SET
                order_no = EXCLUDED.order_no,
                amount_cents = EXCLUDED.amount_cents,
                status = CASE
                    WHEN user_run_unlocks.status = 'rejected' THEN 'pending_payment'
                    ELSE user_run_unlocks.status
                END,
                created_at = now()
            RETURNING *
            """,
            (user_id, run_id, order_no, package_code, amount_cents),
        )

    def get_run_unlock_by_order_no(self, order_no: str) -> dict[str, Any] | None:
        return self._fetchone(
            "SELECT * FROM user_run_unlocks WHERE order_no = %s",
            (order_no,),
        )

    def get_run_unlock(self, user_id: str, run_id: str, package_code: str) -> dict[str, Any] | None:
        return self._fetchone(
            "SELECT * FROM user_run_unlocks WHERE user_id = %s AND run_id = %s AND package_code = %s",
            (user_id, run_id, package_code),
        )

    def list_run_unlocks_by_user(self, user_id: str, run_id: str | None = None) -> list[dict[str, Any]]:
        if run_id:
            return self._fetchall(
                "SELECT * FROM user_run_unlocks WHERE user_id = %s AND run_id = %s ORDER BY created_at DESC",
                (user_id, run_id),
            )
        return self._fetchall(
            "SELECT * FROM user_run_unlocks WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,),
        )

    def list_pending_run_unlocks(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._fetchall(
            """
            SELECT u.*, r.document_id, d.title as document_title
            FROM user_run_unlocks u
            JOIN analysis_runs r ON r.id = u.run_id
            JOIN documents d ON d.id = r.document_id
            WHERE u.status IN ('pending_payment', 'pending_review')
            ORDER BY u.created_at DESC
            LIMIT %s
            """,
            (limit,),
        )

    def update_run_unlock_screenshot(
        self,
        order_no: str,
        payment_method: str,
        screenshot_path: str,
        screenshot_url: str,
    ) -> dict[str, Any] | None:
        return self._fetchone(
            """
            UPDATE user_run_unlocks
            SET payment_method = %s, screenshot_path = %s, screenshot_url = %s, status = 'pending_review'
            WHERE order_no = %s
            RETURNING *
            """,
            (payment_method, screenshot_path, screenshot_url, order_no),
        )

    def approve_run_unlock(self, order_no: str, reviewed_by: str) -> dict[str, Any] | None:
        return self._fetchone(
            """
            UPDATE user_run_unlocks
            SET status = 'unlocked', reviewed_by = %s, reviewed_at = now(), unlocked_at = now()
            WHERE order_no = %s
            RETURNING *
            """,
            (reviewed_by, order_no),
        )

    def reject_run_unlock(self, order_no: str, reviewed_by: str) -> dict[str, Any] | None:
        return self._fetchone(
            """
            UPDATE user_run_unlocks
            SET status = 'rejected', reviewed_by = %s, reviewed_at = now()
            WHERE order_no = %s
            RETURNING *
            """,
            (reviewed_by, order_no),
        )


def _normalize_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            normalized[key] = float(value)
        elif isinstance(value, UUID):
            normalized[key] = str(value)
        else:
            normalized[key] = value
    return normalized


def _merge_json_payload(existing: Any, patch: dict[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    if isinstance(existing, dict):
        merged.update(existing)
    if patch:
        merged.update(patch)
    return merged
