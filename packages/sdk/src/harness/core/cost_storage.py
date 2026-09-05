"""
Cost storage interface for multi-level budget tracking.

Provides storage backends for tracking user-level and global-level usage.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from harness.types import UserUsage

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class GlobalUsage:
    """Global usage statistics."""

    daily_cost_usd: float = 0.0
    daily_tokens: int = 0
    date: str = ""  # YYYY-MM-DD format


class CostStorage(ABC):
    """Abstract base class for cost storage."""

    @abstractmethod
    def get_user_usage(self, user_id: str) -> UserUsage:
        """Get usage for a user."""
        pass

    @abstractmethod
    def record_user_usage(
        self,
        user_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        request: bool = False,
    ) -> UserUsage:
        """Record usage for a user."""
        pass

    @abstractmethod
    def get_global_usage(self) -> GlobalUsage:
        """Get global usage."""
        pass

    @abstractmethod
    def record_global_usage(
        self,
        cost_usd: float = 0.0,
        tokens: int = 0,
    ) -> GlobalUsage:
        """Record global usage."""
        pass

    @abstractmethod
    def reset_daily(self) -> None:
        """Reset daily counters."""
        pass


class InMemoryCostStorage(CostStorage):
    """
    In-memory cost storage.

    Suitable for single-process applications. Data is lost on restart.

    Example:
        >>> storage = InMemoryCostStorage()
        >>> usage = storage.record_user_usage("user-123", input_tokens=1000)
        >>> print(usage.daily_tokens)
    """

    def __init__(self):
        self._user_usage: dict[str, UserUsage] = {}
        self._global_usage = GlobalUsage()
        self._last_reset_date: str = ""

    def _get_current_date(self) -> str:
        """Get current date string."""
        return datetime.now().strftime("%Y-%m-%d")

    def _get_current_hour(self) -> int:
        """Get current hour."""
        return datetime.now().hour

    def _check_and_reset_daily(self) -> None:
        """Check if we need to reset daily counters."""
        current_date = self._get_current_date()
        if current_date != self._last_reset_date:
            self.reset_daily()
            self._last_reset_date = current_date

    def get_user_usage(self, user_id: str) -> UserUsage:
        """Get usage for a user."""
        self._check_and_reset_daily()

        if user_id not in self._user_usage:
            self._user_usage[user_id] = UserUsage(
                user_id=user_id,
                date=self._get_current_date(),
                hour=self._get_current_hour(),
            )

        return self._user_usage[user_id]

    def record_user_usage(
        self,
        user_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        request: bool = False,
    ) -> UserUsage:
        """Record usage for a user."""
        self._check_and_reset_daily()

        if user_id not in self._user_usage:
            self._user_usage[user_id] = UserUsage(
                user_id=user_id,
                date=self._get_current_date(),
                hour=self._get_current_hour(),
            )

        usage = self._user_usage[user_id]

        # Check if we're in a new hour
        current_hour = self._get_current_hour()
        if current_hour != usage.hour:
            usage.hourly_requests = 0
            usage.hour = current_hour

        usage.daily_tokens += input_tokens + output_tokens
        if request:
            usage.hourly_requests += 1

        return usage

    def get_global_usage(self) -> GlobalUsage:
        """Get global usage."""
        self._check_and_reset_daily()
        return self._global_usage

    def record_global_usage(
        self,
        cost_usd: float = 0.0,
        tokens: int = 0,
    ) -> GlobalUsage:
        """Record global usage."""
        self._check_and_reset_daily()

        self._global_usage.daily_cost_usd += cost_usd
        self._global_usage.daily_tokens += tokens

        if not self._global_usage.date:
            self._global_usage.date = self._get_current_date()

        return self._global_usage

    def reset_daily(self) -> None:
        """Reset daily counters."""
        self._user_usage.clear()
        self._global_usage = GlobalUsage(date=self._get_current_date())
        self._last_reset_date = self._get_current_date()


class SQLiteCostStorage(CostStorage):
    """
    SQLite-based cost storage.

    Provides persistent storage for multi-process applications.

    Example:
        >>> storage = SQLiteCostStorage("~/.harness/costs.db")
        >>> usage = storage.record_user_usage("user-123", input_tokens=1000)
    """

    def __init__(self, db_path: str = ".harness/costs.db"):
        from pathlib import Path

        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_usage (
                    user_id TEXT,
                    date TEXT,
                    hour INTEGER,
                    daily_tokens INTEGER DEFAULT 0,
                    hourly_requests INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, date)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS global_usage (
                    date TEXT PRIMARY KEY,
                    daily_cost_usd REAL DEFAULT 0,
                    daily_tokens INTEGER DEFAULT 0
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _get_current_date(self) -> str:
        """Get current date string."""
        return datetime.now().strftime("%Y-%m-%d")

    def _get_current_hour(self) -> int:
        """Get current hour."""
        return datetime.now().hour

    def get_user_usage(self, user_id: str) -> UserUsage:
        """Get usage for a user."""
        import sqlite3

        date = self._get_current_date()
        hour = self._get_current_hour()

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT daily_tokens, hourly_requests, hour "
                "FROM user_usage WHERE user_id = ? AND date = ?",
                (user_id, date),
            )
            row = cursor.fetchone()

            if row:
                stored_hour = row[2]
                # If hour changed, reset hourly counter
                hourly_requests = row[1] if stored_hour == hour else 0
                return UserUsage(
                    user_id=user_id,
                    daily_tokens=row[0],
                    hourly_requests=hourly_requests,
                    date=date,
                    hour=hour,
                )

            return UserUsage(user_id=user_id, date=date, hour=hour)
        finally:
            conn.close()

    def record_user_usage(
        self,
        user_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        request: bool = False,
    ) -> UserUsage:
        """Record usage for a user."""
        import sqlite3

        date = self._get_current_date()
        hour = self._get_current_hour()
        tokens = input_tokens + output_tokens

        conn = sqlite3.connect(self.db_path)
        try:
            # Get current values
            cursor = conn.execute(
                "SELECT daily_tokens, hourly_requests, hour "
                "FROM user_usage WHERE user_id = ? AND date = ?",
                (user_id, date),
            )
            row = cursor.fetchone()

            if row:
                stored_hour = row[2]
                # Reset hourly if hour changed
                hourly_requests = row[1] if stored_hour == hour else 0

                conn.execute(
                    """
                    UPDATE user_usage
                    SET daily_tokens = daily_tokens + ?,
                        hourly_requests = ?,
                        hour = ?
                    WHERE user_id = ? AND date = ?
                """,
                    (
                        tokens,
                        hourly_requests + (1 if request else 0),
                        hour,
                        user_id,
                        date,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO user_usage (user_id, date, hour, daily_tokens, hourly_requests)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (user_id, date, hour, tokens, 1 if request else 0),
                )

            conn.commit()
        finally:
            conn.close()

        return self.get_user_usage(user_id)

    def get_global_usage(self) -> GlobalUsage:
        """Get global usage."""
        import sqlite3

        date = self._get_current_date()

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT daily_cost_usd, daily_tokens FROM global_usage WHERE date = ?",
                (date,),
            )
            row = cursor.fetchone()

            if row:
                return GlobalUsage(
                    daily_cost_usd=row[0],
                    daily_tokens=row[1],
                    date=date,
                )

            return GlobalUsage(date=date)
        finally:
            conn.close()

    def record_global_usage(
        self,
        cost_usd: float = 0.0,
        tokens: int = 0,
    ) -> GlobalUsage:
        """Record global usage."""
        import sqlite3

        date = self._get_current_date()

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO global_usage (date, daily_cost_usd, daily_tokens)
                VALUES (?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    daily_cost_usd = daily_cost_usd + ?,
                    daily_tokens = daily_tokens + ?
            """,
                (date, cost_usd, tokens, cost_usd, tokens),
            )
            conn.commit()
        finally:
            conn.close()

        return self.get_global_usage()

    def reset_daily(self) -> None:
        """Reset daily counters. SQLite version just creates new rows for new day."""
        pass  # SQLite automatically handles new dates
