"""
Match Spider — Scrapes recent and upcoming cricket match data.

Primary target: Cricbuzz match listings (recent results)
Secondary target: ESPN Cricinfo match results

Extracts series name, teams, date, venue, and result.
"""

import scrapy
from cricket_scraper.items import MatchItem


class MatchSpider(scrapy.Spider):
    """Crawl match results and fixtures from cricket websites."""

    name = "matches"
    allowed_domains = ["www.cricbuzz.com", "www.espncricinfo.com"]

    start_urls = [
        # Cricbuzz recent match results
        "https://www.cricbuzz.com/cricket-match/live-scores/recent-matches",
        # Cricbuzz upcoming matches
        "https://www.cricbuzz.com/cricket-match/live-scores/upcoming-matches",
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    }

    def parse(self, response):
        """Parse match listing pages.

        Cricbuzz lists matches in card-style blocks grouped by series.
        Each card contains team names, result, date, and venue.
        """
        self.logger.info("Parsing match listing: %s (status %s)", response.url, response.status)

        # Current series context
        current_series = ""

        # Cricbuzz groups matches under series headers
        # Iterate through all child elements in the matches container
        content_blocks = response.css("div.cb-col.cb-col-100.cb-plyr-tbody")

        for block in content_blocks:
            # Check if this is a series header
            series_header = block.css("h2.cb-lv-grn-strip::text").get("")
            if series_header:
                current_series = series_header.strip()
                continue

            # Extract match cards within this block
            match_cards = block.css("div.cb-mtch-lst.cb-col.cb-col-100")
            if not match_cards:
                match_cards = block.css("div.cb-col-100.cb-col")

            for card in match_cards:
                yield from self._parse_match_card(card, current_series)

        # Also try a flatter structure
        all_match_items = response.css("div.cb-mtch-lst.cb-col.cb-col-100.cb-tms-itm")
        if all_match_items:
            for card in all_match_items:
                yield from self._parse_match_card(card, "")

        # Fallback: iterate through all list group items
        list_items = response.css("div.cb-sch-lst-itm")
        for item in list_items:
            yield from self._parse_schedule_item(item, current_series)

    def _parse_match_card(self, card, series_name: str):
        """Extract match data from a Cricbuzz match card element.

        Args:
            card: Scrapy Selector for the match card.
            series_name: Name of the series this match belongs to.

        Yields:
            MatchItem if sufficient data is extracted.
        """
        # --- Teams ---
        team_elements = card.css("div.cb-hmscg-tm-name::text").getall()
        if len(team_elements) < 2:
            # Fallback selectors
            team_elements = card.css("a.cb-lv-scrs-well-live::text, a.cb-lv-scrs-well::text").getall()
        if len(team_elements) < 2:
            team_elements = card.css("div.cb-ovr-flo::text").getall()

        team1 = team_elements[0].strip() if len(team_elements) > 0 else ""
        team2 = team_elements[1].strip() if len(team_elements) > 1 else ""

        if not team1 or not team2:
            return

        # --- Series (from header context or from card) ---
        if not series_name:
            series_name = card.css("div.cb-lv-scrs-hdr-rw span::text").get("").strip()

        # --- Result ---
        result = card.css("div.cb-text-complete::text").get("").strip()
        if not result:
            result = card.css("a.cb-text-complete::text").get("").strip()
        if not result:
            result = card.css("div.cb-lv-scrs-well span.cb-text-complete::text").get("").strip()

        # --- Venue ---
        venue = card.css("div.text-gray span::text").get("").strip()
        if not venue:
            venue = card.css("span.cb-font-12.text-gray::text").get("").strip()

        # --- Date ---
        match_date = card.css("span.schedule-date::text").get("").strip()
        if not match_date:
            match_date = card.css("div.cb-lv-scrs-well span.text-gray::text").get("").strip()

        yield MatchItem(
            series=series_name,
            team1=team1,
            team2=team2,
            date=match_date,
            venue=venue,
            result=result,
        )

    def _parse_schedule_item(self, item, series_name: str):
        """Parse a match from the schedule/recent format.

        Args:
            item: Scrapy Selector for the schedule list item.
            series_name: Current series context.

        Yields:
            MatchItem if sufficient data is extracted.
        """
        # Extract match title (usually contains team names)
        title = item.css("a::text").get("").strip()
        if not title:
            return

        # Try to split teams from title (e.g., "India vs Australia")
        team1, team2 = "", ""
        for sep in [" vs ", " v ", " VS "]:
            if sep in title:
                parts = title.split(sep, 1)
                team1 = parts[0].strip()
                team2 = parts[1].strip()
                break

        if not team1 or not team2:
            return

        venue = item.css("div.text-gray::text").get("").strip()
        match_date = item.css("span.schedule-date::text").get("").strip()
        result = item.css("div.cb-text-complete::text").get("").strip()

        yield MatchItem(
            series=series_name,
            team1=team1,
            team2=team2,
            date=match_date,
            venue=venue,
            result=result,
        )

    def handle_error(self, failure):
        """Log request failures without crashing."""
        self.logger.error("Request failed: %s — %s", failure.request.url, failure.value)
