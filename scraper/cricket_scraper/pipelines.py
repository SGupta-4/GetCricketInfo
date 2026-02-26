"""
Scrapy Pipelines for the Cricket Scraper project.

DataCleaningPipeline — sanitises and normalises scraped data.
SQLitePipeline — writes items directly to SQLite via CricketDB.
"""

import sys
import os
import logging

# Add project root to path so we can import the database module
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from database.db_manager import CricketDB  # noqa: E402
from cricket_scraper.items import PlayerItem, TeamItem, SeriesItem, MatchItem  # noqa: E402

logger = logging.getLogger(__name__)


class DataCleaningPipeline:
    """Cleans and normalises scraped item data before storage.

    - Strips whitespace from string fields
    - Converts numeric strings to int/float
    - Replaces None with sensible defaults
    """

    def process_item(self, item, spider):
        """Clean every field in the item."""
        for field in item.fields:
            value = item.get(field, "")
            if isinstance(value, str):
                item[field] = value.strip()
            elif value is None:
                item[field] = ""
        # Ensure numeric fields are properly typed
        if isinstance(item, PlayerItem):
            item["matches"] = self._to_int(item.get("matches", 0))
            item["runs"] = self._to_int(item.get("runs", 0))
            item["wickets"] = self._to_int(item.get("wickets", 0))
            item["average"] = self._to_float(item.get("average", 0.0))
            item["strike_rate"] = self._to_float(item.get("strike_rate", 0.0))
        if isinstance(item, TeamItem):
            item["ranking"] = self._to_int(item.get("ranking", 0))
        return item

    @staticmethod
    def _to_int(value) -> int:
        """Safely convert a value to int."""
        try:
            return int(str(value).replace(",", "").strip() or 0)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _to_float(value) -> float:
        """Safely convert a value to float."""
        try:
            return float(str(value).replace(",", "").strip() or 0.0)
        except (ValueError, TypeError):
            return 0.0


class SQLitePipeline:
    """Writes scraped items directly to SQLite.

    Opens a CricketDB connection when the spider starts and calls the
    appropriate upsert method for each item type.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db = None

    @classmethod
    def from_crawler(cls, crawler):
        """Read DB path from Scrapy settings."""
        db_path = crawler.settings.get("SQLITE_DB_PATH")
        if not db_path:
            raise ValueError("SQLITE_DB_PATH must be set in settings.py")
        return cls(db_path=db_path)

    def open_spider(self, spider):
        """Initialise database and create tables if needed."""
        logger.info("SQLitePipeline: opening database at %s", self.db_path)
        self.db = CricketDB(self.db_path)
        self.db.init_db()

    def close_spider(self, spider):
        """Clean up (connections are opened/closed per operation in CricketDB)."""
        logger.info("SQLitePipeline: spider closed, data committed")

    def process_item(self, item, spider):
        """Route item to the correct upsert method."""
        data = dict(item)

        if isinstance(item, PlayerItem):
            self.db.upsert_player(data)
        elif isinstance(item, TeamItem):
            self.db.upsert_team(data)
        elif isinstance(item, SeriesItem):
            self.db.upsert_series(data)
        elif isinstance(item, MatchItem):
            self.db.upsert_match(data)
        else:
            logger.warning("Unknown item type: %s", type(item).__name__)

        return item
