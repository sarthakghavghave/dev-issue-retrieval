from typing import Iterable, Sequence

import pandas as pd
from sqlalchemy import bindparam, create_engine, text

from scripts.config import build_database_url

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(build_database_url(), pool_pre_ping=True)
    return _engine


PENDING_QUERY = """
SELECT
    id,
    github_issue_id,
    repository_name,
    title,
    body,
    labels,
    issue_url,
    created_at,
    updated_at,
    comments,
    comments_url,
    index_status,
    filter_reason
FROM issues
WHERE index_status = 'PENDING'
ORDER BY id
LIMIT :limit
"""

INDEXED_KEYS_QUERY = """
SELECT LOWER(TRIM(title)) AS title_key, LOWER(TRIM(repository_name)) AS repo_key
FROM issues
WHERE index_status = 'INDEXED'
  AND title IS NOT NULL
  AND repository_name IS NOT NULL
"""


def fetch_pending_issues(limit: int) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(PENDING_QUERY), conn, params={"limit": limit})


def fetch_indexed_title_keys() -> set:
    with get_engine().connect() as conn:
        df = pd.read_sql(text(INDEXED_KEYS_QUERY), conn)

    if df.empty:
        return set()

    return {
        (row["title_key"], row["repo_key"])
        for _, row in df.iterrows()
        if row["title_key"] and row["repo_key"]
    }


def mark_indexing(issue_ids: Sequence[int]) -> int:
    if not issue_ids:
        return 0

    stmt = text(
        """
        UPDATE issues
        SET index_status = 'INDEXING'
        WHERE id IN :ids
          AND index_status = 'PENDING'
        """
    ).bindparams(bindparam("ids", expanding=True))
    with get_engine().begin() as conn:
        result = conn.execute(stmt, {"ids": list(issue_ids)})
        return result.rowcount


def update_issue_status(
    issue_id: int,
    index_status: str,
    filter_reason: str = "NONE",
) -> None:
    stmt = text(
        """
        UPDATE issues
        SET index_status = :index_status,
            filter_reason = :filter_reason
        WHERE id = :issue_id
        """
    )
    with get_engine().begin() as conn:
        conn.execute(
            stmt,
            {
                "issue_id": issue_id,
                "index_status": index_status,
                "filter_reason": filter_reason,
            },
        )


def update_issues_status_batch(
    updates: Iterable[tuple],
) -> None:
    """Batch-update (issue_id, index_status, filter_reason) tuples."""
    rows = list(updates)
    if not rows:
        return

    stmt = text(
        """
        UPDATE issues
        SET index_status = :index_status,
            filter_reason = :filter_reason
        WHERE id = :issue_id
        """
    )
    params = [
        {
            "issue_id": issue_id,
            "index_status": index_status,
            "filter_reason": filter_reason,
        }
        for issue_id, index_status, filter_reason in rows
    ]
    with get_engine().begin() as conn:
        for param in params:
            conn.execute(stmt, param)


def count_by_status(status: str) -> int:
    stmt = text("SELECT COUNT(*) FROM issues WHERE index_status = :status")
    with get_engine().connect() as conn:
        return conn.execute(stmt, {"status": status}).scalar_one()
