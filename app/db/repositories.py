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
        return self._fetchone("SELECT * FROM documents WHERE doc_hash = %s", (doc_hash,))

    def create_user(self, *, email: str, password_hash: str, display_name: str) -> dict[str, Any]:
        return self._fetchone(
            """
            INSERT INTO app_users (email, password_hash, display_name, status, credits_balance)
            VALUES (%s, %s, %s, 'active', 0)
            RETURNING *
            """,
            (email, password_hash, display_name),
        )

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self._fetchone("SELECT * FROM app_users WHERE id = %s", (user_id,))

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return self._fetchone("SELECT * FROM app_users WHERE email = %s", (email,))

    def delete_user(self, user_id: str) -> bool:
        """删除用户及其关联数据（GDPR/个人信息保护法删除权）。"""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                # 外键约束会自动级联删除 billing_orders, credit_ledger,
                # user_document_access, user_sessions 等
                cur.execute("DELETE FROM app_users WHERE id = %s RETURNING id", (user_id,))
                row = cur.fetchone()
            conn.commit()
        return row is not None

    def export_user_data(self, user_id: str) -> dict[str, Any]:
        """导出用户全部个人数据（GDPR/个人信息保护法查阅权）。"""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, email, display_name, status, credits_balance, created_at, updated_at FROM app_users WHERE id = %s", (user_id,))
                user = cur.fetchone()

                cur.execute("SELECT id, task_type, status, progress, created_at, finished_at FROM analysis_tasks WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
                tasks = cur.fetchall()

                cur.execute("SELECT id, order_no, package_code, status, amount_cents, credits, created_at, paid_at FROM billing_orders WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
                orders = cur.fetchall()

                cur.execute("SELECT id, change_amount, balance_after, source_type, note, created_at FROM credit_ledger WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
                ledger = cur.fetchall()

                cur.execute("SELECT document_id, created_at FROM user_document_access WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
                accesses = cur.fetchall()

                try:
                    cur.execute("SELECT id, action, resource_type, resource_id, created_at FROM audit_logs WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
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

    def create_user_session(self, *, user_id: str, token_hash: str, expires_at: Any) -> dict[str, Any]:
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
                cur.execute("SELECT * FROM app_users WHERE id = %s FOR UPDATE", (user_id,))
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
        return self._fetchone("SELECT * FROM billing_orders WHERE order_no = %s", (order_no,))

    def get_user_billing_order(self, user_id: str, order_no: str) -> dict[str, Any] | None:
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
                cur.execute("SELECT * FROM billing_orders WHERE order_no = %s FOR UPDATE", (order_no,))
                order = cur.fetchone()
                if order is None:
                    raise ValueError("order not found")

                order_status = str(order.get("status") or "")
                user_id = str(order["user_id"])

                if order_status == "paid":
                    cur.execute("SELECT credits_balance FROM app_users WHERE id = %s", (user_id,))
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

                merged_payload = _merge_json_payload(order.get("payment_payload"), payment_payload)

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

                cur.execute("SELECT * FROM app_users WHERE id = %s FOR UPDATE", (user_id,))
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
                    (user_id, int(order["credits"]), new_balance, "order_purchase", order["id"], note),
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

    def can_user_access_document(self, *, user_id: str | None, document_id: str) -> bool:
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
    ) -> dict[str, Any]:
        query = """
            INSERT INTO analysis_runs (document_id, run_type, provider, provider_version, status)
            VALUES (%s, %s, %s, %s, 'queued')
            RETURNING *
        """
        return self._fetchone(query, (document_id, run_type, provider, provider_version))

    def mark_document_status(self, document_id: str, status: str, *, section_count: int | None = None) -> None:
        if section_count is None:
            self._execute("UPDATE documents SET status = %s, updated_at = now() WHERE id = %s", (status, document_id))
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
        self._execute("UPDATE analysis_runs SET status = 'completed', finished_at = now() WHERE id = %s", (run_id,))

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

    def list_completed_runs(self, document_id: str, limit: int = 1) -> list[dict[str, Any]]:
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

    def create_analysis_task(self, *, user_id: str | None, document_id: str, task_type: str = "analysis") -> dict[str, Any]:
        return self._fetchone(
            """
            INSERT INTO analysis_tasks (user_id, document_id, task_type, status, progress, result_json)
            VALUES (%s, %s, %s, 'queued', 0, '{}'::jsonb)
            RETURNING *
            """,
            (user_id, document_id, task_type),
        )

    def mark_analysis_task_processing(self, task_id: str, *, progress: int = 35) -> None:
        self._execute(
            """
            UPDATE analysis_tasks
            SET status = 'processing', progress = %s, started_at = COALESCE(started_at, now()), error_message = NULL
            WHERE id = %s
            """,
            (progress, task_id),
        )

    def mark_analysis_task_completed(self, task_id: str, *, run_id: str, result_json: dict[str, Any]) -> None:
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

    def list_user_analysis_tasks(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
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

    def list_cnki_feedback_for_document(self, document_id: str, limit: int = 20) -> list[dict[str, Any]]:
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

    def insert_document_sections(self, document_id: str, sections: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
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
                section.get("section_title"),
                section.get("text_preview"),
                section["content"],
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
            (embedding_str, exclude_document_id, embedding_str, distance_threshold, embedding_str, limit),
        )

    def insert_section_scores(self, run_id: str, scores: Sequence[dict[str, Any]]) -> None:
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
                            Jsonb(score.get("reasons", [])),
                            Jsonb(score.get("signals", [])),
                        ),
                    )
            conn.commit()

    def insert_similarity_matches(self, run_id: str, matches: Sequence[dict[str, Any]]) -> None:
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
                            match.get("matched_source"),
                            match.get("matched_title"),
                            match.get("matched_snippet"),
                            match["similarity_score"],
                            match.get("overlap_chars", 0),
                            match.get("match_type"),
                            match.get("source_url"),
                        ),
                    )
            conn.commit()

    def insert_provider_payload(self, run_id: str, provider: str, payload_type: str, payload: dict[str, Any]) -> None:
        self._execute(
            """
            INSERT INTO provider_payloads (run_id, provider, payload_type, payload)
            VALUES (%s, %s, %s, %s)
            """,
            (run_id, provider, payload_type, Jsonb(jsonable_encoder(payload))),
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
            (run_id, provider, payload_type, Jsonb(jsonable_encoder(payload))),
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
                Jsonb(jsonable_encoder(summary)),
            ),
        )

    def save_report_snapshot(self, *, document_id: str, run_id: str, report_json: dict[str, Any]) -> dict[str, Any]:
        query = """
            INSERT INTO report_snapshots (document_id, run_id, report_json)
            VALUES (%s, %s, %s)
            RETURNING *
        """
        return self._fetchone(query, (document_id, run_id, Jsonb(jsonable_encoder(report_json))))

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

    def get_active_model(self, model_type: str, scene_key: str | None) -> dict[str, Any] | None:
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
                json.dumps(details) if details else "{}",
                verified,
            ),
        )

    def _fetchone(self, query: str, params: Sequence[Any]) -> dict[str, Any] | None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()
            conn.commit()
        return _normalize_row(row)

    def _fetchall(self, query: str, params: Sequence[Any]) -> list[dict[str, Any]]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
            conn.commit()
        return [_normalize_row(row) for row in rows]

    def _execute(self, query: str, params: Sequence[Any]) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
            conn.commit()


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
