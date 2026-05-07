import time
from functools import lru_cache

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import get_settings


@lru_cache
def get_connection_pool() -> ConnectionPool:
    settings = get_settings()
    pool = ConnectionPool(
        conninfo=settings.database_url,
        min_size=settings.database_pool_min,
        max_size=settings.database_pool_max,
        kwargs={"autocommit": False, "row_factory": dict_row},
        open=False,
    )
    # 启动时带重试打开连接池（适配 Docker Compose 启动顺序）
    last_exc = None
    for attempt in range(10):
        try:
            pool.open(wait=True)
            break
        except Exception as exc:
            last_exc = exc
            time.sleep(min(2 ** attempt, 30))
    else:
        raise RuntimeError(f"Database connection failed after 10 attempts: {last_exc}")
    return pool


def close_connection_pool() -> None:
    pool = get_connection_pool()
    if not pool.closed:
        pool.close()
