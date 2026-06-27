"""
Series Spider — Scrapes cricket series and tournament information.

Primary target: Cricbuzz series archive
Secondary target: ESPN Cricinfo series pages

Extracts series name, host country, dates, and winner.
"""

import scrapy
from cricket_scraper.items import SeriesItem


class SeriesSpider(scrapy.Spider):
    """Crawl series/tournament information from cricket websites."""

    name = "series"
    allowed_domains = ["www.cricbuzz.com", "www.espncricinfo.com"]

    start_urls = [
        "https://www.cricbuzz.com/cricket-series",
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    }

    def parse(self, response):
        """Parse series listing pages.

        Cricbuzz series pages list ongoing, upcoming, and recent series
        with links to their detail pages.
        """
        self.logger.info("Parsing series listing: %s (status %s)", response.url, response.status)

        # Find series entries — Cricbuzz uses list items
        series_links = response.css('div.bg-white.px-4.py-3.mb-1 a[href*="/cricket-series/"]')

        seen_urls = set()
        for link in series_links:
            href = link.attrib.get("href", "")
            series_name = link.css("div.text-ellipsis::text").get("").strip()
            if not series_name:
                series_name = link.css("::text").get("").strip()

            # Filter out navigation/category links
            if (
                not href
                or not series_name
                or len(series_name) < 3
                or "/international" in href
                or "/domestic" in href
                or "/league" in href
                or "/women" in href
            ):
                continue

            full_url = response.urljoin(href)
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            yield scrapy.Request(
                url=full_url,
                callback=self.parse_series_detail,
                errback=self.handle_error,
                meta={"series_name": series_name},
            )

        # Pagination: look for "next" or "more" links
        next_page = response.css('a.cb-nav-next::attr(href)').get()
        if next_page:
            yield scrapy.Request(
                url=response.urljoin(next_page),
                callback=self.parse,
                errback=self.handle_error,
            )

    def parse_series_detail(self, response):
        """Parse an individual series detail page.

        Extracts host country, date range, and winner (if completed).
        """
        self.logger.info("Parsing series detail: %s", response.url)

        series_name = response.meta.get("series_name", "")
        if not series_name:
            series_name = response.css("h1::text").get("").strip()

        # --- Extract date range ---
        start_date = ""
        end_date = ""
        date_text = response.css("div.cb-series-date::text").get("")
        if not date_text:
            date_text = response.css("span.schedule-date::text").get("")
        if date_text:
            # Cricbuzz often shows dates as "Jan 01 - Feb 15, 2025"
            parts = date_text.strip().split(" - ")
            if len(parts) == 2:
                start_date = parts[0].strip()
                end_date = parts[1].strip()
            else:
                start_date = date_text.strip()

        # --- Extract host ---
        host = ""
        venue_elements = response.css("div.cb-col.cb-col-67 div.cb-col-100.cb-col::text").getall()
        for el in venue_elements:
            text = el.strip()
            if text and len(text) > 2:
                # Last word is often the country
                host = text
                break

        # Fallback: try to extract from breadcrumb or meta
        if not host:
            breadcrumb_links = response.css("div.cb-col.cb-breadcrumb a::text").getall()
            for bc in breadcrumb_links:
                bc = bc.strip()
                if bc and bc.lower() not in ("home", "cricket", "series"):
                    host = bc
                    break

        # --- Extract winner ---
        winner = ""
        result_text = response.css("div.cb-srs-result span::text").get("")
        if not result_text:
            result_text = response.css("div.cb-winners::text").get("")
        if result_text:
            winner = result_text.strip()

        yield SeriesItem(
            name=series_name,
            host=host,
            start_date=start_date,
            end_date=end_date,
            winner=winner,
        )

    def handle_error(self, failure):
        """Log request failures without crashing."""
        self.logger.error("Request failed: %s — %s", failure.request.url, failure.value)
