"""
Scrapy settings for the Cricket Scraper project.

Optimized for polite crawling, AWS Free Tier resource constraints,
and direct SQLite storage via pipeline.
"""

import os

BOT_NAME = "cricket_scraper"
SPIDER_MODULES = ["cricket_scraper.spiders"]
NEWSPIDER_MODULE = "cricket_scraper.spiders"

# ---------- Crawl behaviour ----------

# Be polite: 2-second delay between requests
DOWNLOAD_DELAY = 2

# Auto-throttle adjusts delay dynamically based on server load
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# Retry on failures
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Timeouts
DOWNLOAD_TIMEOUT = 30

# Do not obey robots.txt (needed for data access on some sites)
ROBOTSTXT_OBEY = False

# Concurrency — keep low for AWS Free Tier (1 GB RAM)
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2

# ---------- User-Agent ----------

# Default UA (overridden per-request by middleware)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ---------- Middlewares ----------

DOWNLOADER_MIDDLEWARES = {
    "cricket_scraper.middlewares.RotateUserAgentMiddleware": 400,
}

# ---------- Pipelines ----------

# Database path: resolve relative to the project root
_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "database", "cricket.db"
)

ITEM_PIPELINES = {
    "cricket_scraper.pipelines.DataCleaningPipeline": 100,
    "cricket_scraper.pipelines.SQLitePipeline": 300,
}

SQLITE_DB_PATH = _DB_PATH

# ---------- Logging ----------

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

# ---------- Caching (optional, saves bandwidth during dev) ----------

# Uncomment to enable cache during development:
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 86400
# HTTPCACHE_DIR = "httpcache"

# ---------- Feeds ----------

# No feed exports — all data goes through SQLite pipeline.
# FEEDS = {}

# ---------- Request fingerprinting ----------

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
