"""
Dedup Store - Incremental deduplication using SQLite.

Prevents processing the same URL multiple times.
"""

import hashlib
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class DedupStore:
    """
    Deduplication store using SQLite.

    Stores URL hashes to prevent re-processing.
    Lightweight and persistent.
    """

    def __init__(self, db_path: str = "~/.harness/scraper/seen.db"):
        """
        Initialize dedup store.

        Args:
            db_path: SQLite database path
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_table()

    def _init_table(self):
        """Create table if not exists"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_urls (
                url_hash TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                concept_name TEXT,
                seen_at TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def _hash_url(self, url: str) -> str:
        """Generate MD5 hash of URL"""
        return hashlib.md5(url.encode()).hexdigest()

    def is_seen(self, url: str) -> bool:
        """
        Check if URL has been processed.

        Args:
            url: URL to check

        Returns:
            True if already seen
        """
        url_hash = self._hash_url(url)
        cursor = self.conn.execute(
            "SELECT 1 FROM seen_urls WHERE url_hash = ?",
            (url_hash,)
        )
        return cursor.fetchone() is not None

    def mark_seen(self, url: str, concept_name: str = ""):
        """
        Mark URL as processed.

        Args:
            url: URL to mark
            concept_name: Optional concept name
        """
        url_hash = self._hash_url(url)
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT OR IGNORE INTO seen_urls (url_hash, url, concept_name, seen_at) VALUES (?, ?, ?, ?)",
            (url_hash, url, concept_name, now)
        )
        self.conn.commit()

    def get_recent(self, limit: int = 50) -> list[dict]:
        """
        Get recently processed URLs.

        Args:
            limit: Maximum number to return

        Returns:
            List of dicts with url, concept_name, seen_at
        """
        cursor = self.conn.execute(
            """
            SELECT url, concept_name, seen_at FROM seen_urls
            ORDER BY seen_at DESC LIMIT ?
            """,
            (limit,)
        )
        return [
            {"url": row[0], "concept_name": row[1], "seen_at": row[2]}
            for row in cursor.fetchall()
        ]

    def close(self):
        """Close database connection"""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()