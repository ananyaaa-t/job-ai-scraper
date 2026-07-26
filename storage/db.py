"""
SQLite-backed storage for scraped job postings: dedup, fit-evaluation results,
and application status tracking so the same job is never re-emailed twice.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from config.settings import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS postings (
    id              TEXT PRIMARY KEY,   -- stable hash of (source, company, title, url)
    title           TEXT NOT NULL,
    company         TEXT NOT NULL,
    location        TEXT,
    url             TEXT NOT NULL,
    description     TEXT,
    source          TEXT NOT NULL,      -- e.g. 'greenhouse:notion', 'yc', 'wellfound'
    priority_tier   TEXT NOT NULL,      -- 'priority0' | 'startup'
    posted_date     TEXT,
    first_seen_at   TEXT NOT NULL,
    fit_score       INTEGER,
    fit_reasoning   TEXT,
    tailored_bullets TEXT,
    cover_letter_draft TEXT,
    status          TEXT NOT NULL DEFAULT 'new',  -- new | evaluated | emailed | prefilled | applied | skipped
    emailed_at      TEXT
);
"""


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_posting(posting: dict) -> bool:
    """Insert a posting if not already seen. Returns True if newly inserted."""
    with get_conn() as conn:
        cur = conn.execute("SELECT 1 FROM postings WHERE id = ?", (posting["id"],))
        if cur.fetchone():
            return False
        conn.execute(
            """INSERT INTO postings
               (id, title, company, location, url, description, source, priority_tier,
                posted_date, first_seen_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
            (
                posting["id"], posting["title"], posting["company"], posting.get("location"),
                posting["url"], posting.get("description"), posting["source"],
                posting["priority_tier"], posting.get("posted_date"),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        return True


def save_evaluation(posting_id: str, fit_score: int, reasoning: str, bullets: str, cover_letter: str):
    with get_conn() as conn:
        conn.execute(
            """UPDATE postings
               SET fit_score = ?, fit_reasoning = ?, tailored_bullets = ?,
                   cover_letter_draft = ?, status = 'evaluated'
               WHERE id = ?""",
            (fit_score, reasoning, bullets, cover_letter, posting_id),
        )


def mark_status(posting_id: str, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE postings SET status = ? WHERE id = ?", (status, posting_id))


def mark_emailed(posting_ids: list[str]):
    with get_conn() as conn:
        now = datetime.now(timezone.utc).isoformat()
        conn.executemany(
            "UPDATE postings SET status = 'emailed', emailed_at = ? WHERE id = ?",
            [(now, pid) for pid in posting_ids],
        )


def get_new_postings() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM postings WHERE status = 'new'").fetchall()


def get_postings_to_email(min_fit_score: int) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            """SELECT * FROM postings
               WHERE status = 'evaluated' AND fit_score >= ?
               ORDER BY fit_score DESC""",
            (min_fit_score,),
        ).fetchall()
