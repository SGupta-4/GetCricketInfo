"""
Database Manager for Cricket Analytics Dashboard.

Provides a CricketDB class that wraps SQLite operations with
parameterized queries, upsert support, and easy PostgreSQL migration path.
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional


# Default path to the database file (relative to this module)
_DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "cricket.db")
_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


class CricketDB:
    """Thread-safe SQLite database manager for cricket analytics data.

    Attributes:
        db_path: Absolute path to the SQLite database file.
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize with a database path.

        Args:
            db_path: Path to SQLite DB file. Use ':memory:' for testing.
                     Defaults to database/cricket.db.
        """
        self.db_path = db_path or _DEFAULT_DB_PATH

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        """Create a new connection with row-factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # better concurrency
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_db(self) -> None:
        """Create all tables and indexes from schema.sql."""
        schema_path = _SCHEMA_PATH
        # For in-memory DBs or when schema.sql is alongside this file
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
        else:
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        conn = self._connect()
        try:
            conn.executescript(schema_sql)
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Upsert methods (INSERT OR REPLACE)
    # ------------------------------------------------------------------

    def upsert_player(self, data: dict) -> None:
        """Insert or update a player record.

        Args:
            data: Dictionary with keys matching the players table columns.
        """
        sql = """
            INSERT INTO players (name, country, role, batting_style, bowling_style,
                                 matches, runs, wickets, average, strike_rate, profile_url,
                                 updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(profile_url) DO UPDATE SET
                name         = excluded.name,
                country      = excluded.country,
                role         = excluded.role,
                batting_style = excluded.batting_style,
                bowling_style = excluded.bowling_style,
                matches      = excluded.matches,
                runs         = excluded.runs,
                wickets      = excluded.wickets,
                average      = excluded.average,
                strike_rate  = excluded.strike_rate,
                updated_at   = CURRENT_TIMESTAMP
        """
        conn = self._connect()
        try:
            conn.execute(sql, (
                data.get("name", ""),
                data.get("country", ""),
                data.get("role", ""),
                data.get("batting_style", ""),
                data.get("bowling_style", ""),
                int(data.get("matches", 0) or 0),
                int(data.get("runs", 0) or 0),
                int(data.get("wickets", 0) or 0),
                float(data.get("average", 0.0) or 0.0),
                float(data.get("strike_rate", 0.0) or 0.0),
                data.get("profile_url", ""),
            ))
            conn.commit()
        finally:
            conn.close()

    def upsert_team(self, data: dict) -> None:
        """Insert or update a team record."""
        sql = """
            INSERT INTO teams (team_name, country, captain, coach, ranking, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(team_name) DO UPDATE SET
                country    = excluded.country,
                captain    = excluded.captain,
                coach      = excluded.coach,
                ranking    = excluded.ranking,
                updated_at = CURRENT_TIMESTAMP
        """
        conn = self._connect()
        try:
            conn.execute(sql, (
                data.get("team_name", ""),
                data.get("country", ""),
                data.get("captain", ""),
                data.get("coach", ""),
                int(data.get("ranking", 0) or 0),
            ))
            conn.commit()
        finally:
            conn.close()

    def upsert_series(self, data: dict) -> None:
        """Insert or update a series record."""
        sql = """
            INSERT INTO series (name, host, start_date, end_date, winner, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name, start_date) DO UPDATE SET
                host       = excluded.host,
                end_date   = excluded.end_date,
                winner     = excluded.winner,
                updated_at = CURRENT_TIMESTAMP
        """
        conn = self._connect()
        try:
            conn.execute(sql, (
                data.get("name", ""),
                data.get("host", ""),
                data.get("start_date", ""),
                data.get("end_date", ""),
                data.get("winner", ""),
            ))
            conn.commit()
        finally:
            conn.close()

    def upsert_match(self, data: dict) -> None:
        """Insert or update a match record."""
        sql = """
            INSERT INTO matches (series, team1, team2, date, venue, result, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(team1, team2, date, venue) DO UPDATE SET
                series     = excluded.series,
                result     = excluded.result,
                updated_at = CURRENT_TIMESTAMP
        """
        conn = self._connect()
        try:
            conn.execute(sql, (
                data.get("series", ""),
                data.get("team1", ""),
                data.get("team2", ""),
                data.get("date", ""),
                data.get("venue", ""),
                data.get("result", ""),
            ))
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Query methods (read)
    # ------------------------------------------------------------------

    def get_players(self, country: Optional[str] = None,
                    role: Optional[str] = None,
                    search: Optional[str] = None,
                    limit: int = 200) -> list[dict]:
        """Fetch players with optional filters.

        Args:
            country: Filter by country (exact match).
            role: Filter by role (exact match).
            search: Search player name (LIKE match).
            limit: Maximum rows to return.

        Returns:
            List of player dicts.
        """
        sql = "SELECT * FROM players WHERE 1=1"
        params: list = []

        if country:
            sql += " AND country = ?"
            params.append(country)
        if role:
            sql += " AND role = ?"
            params.append(role)
        if search:
            sql += " AND name LIKE ?"
            params.append(f"%{search}%")

        sql += " ORDER BY runs DESC LIMIT ?"
        params.append(limit)

        conn = self._connect()
        try:
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_player_by_id(self, player_id: int) -> Optional[dict]:
        """Fetch a single player by ID."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM players WHERE id = ?", (player_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_player_names(self) -> list[str]:
        """Fetch all player names for autocomplete."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT name FROM players ORDER BY name LIMIT 1000"
            ).fetchall()
            return [row["name"] for row in rows]
        finally:
            conn.close()

    def get_teams(self, limit: int = 50) -> list[dict]:
        """Fetch all teams ordered by ranking."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM teams ORDER BY ranking ASC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_team_names(self) -> list[str]:
        """Fetch all team names."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT team_name FROM teams ORDER BY team_name"
            ).fetchall()
            return [row["team_name"] for row in rows]
        finally:
            conn.close()

    def get_series(self, limit: int = 100) -> list[dict]:
        """Fetch all series ordered by start date descending."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM series ORDER BY start_date DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_series_names(self) -> list[str]:
        """Fetch all series names."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT DISTINCT name FROM series ORDER BY name"
            ).fetchall()
            return [row["name"] for row in rows]
        finally:
            conn.close()

    def get_matches(self, team: Optional[str] = None,
                    series: Optional[str] = None,
                    limit: int = 200) -> list[dict]:
        """Fetch matches with optional filters."""
        sql = "SELECT * FROM matches WHERE 1=1"
        params: list = []

        if team:
            sql += " AND (team1 = ? OR team2 = ?)"
            params.extend([team, team])
        if series:
            sql += " AND series = ?"
            params.append(series)

        sql += " ORDER BY date DESC LIMIT ?"
        params.append(limit)

        conn = self._connect()
        try:
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Aggregate / stats queries
    # ------------------------------------------------------------------

    def get_counts(self) -> dict:
        """Return total counts for the overview page."""
        conn = self._connect()
        try:
            counts = {}
            for table in ("players", "teams", "series", "matches"):
                row = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table}").fetchone()
                counts[table] = row["cnt"] if row else 0
            return counts
        finally:
            conn.close()

    def get_distinct_countries(self) -> list[str]:
        """Fetch distinct player countries for filter dropdowns."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT DISTINCT country FROM players WHERE country != '' ORDER BY country"
            ).fetchall()
            return [row["country"] for row in rows]
        finally:
            conn.close()

    def get_distinct_roles(self) -> list[str]:
        """Fetch distinct player roles for filter dropdowns."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT DISTINCT role FROM players WHERE role != '' ORDER BY role"
            ).fetchall()
            return [row["role"] for row in rows]
        finally:
            conn.close()
