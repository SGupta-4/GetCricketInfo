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

        # Each series group is a div under div.flex.flex-col.gap-2
        series_groups = response.css("div.flex.flex-col.gap-2 > div")
        
        found_matches = False
        for group in series_groups:
            series_name = group.css('a[href*="/cricket-series/"]::text').get("")
            if not series_name:
                series_name = group.css('a[href*="/cricket-series/"] span::text').get("")
            
            series_name = series_name.strip() if series_name else ""
            if not series_name:
                continue

            match_cards = group.css('a[href*="/live-cricket-scores/"].bg-cbWhite')
            for card in match_cards:
                found_matches = True
                yield from self._parse_match_card(card, series_name)

        if not found_matches:
            # Fallback to old selectors if page layout reverts
            self.logger.info("Using fallback matches parser")
            content_blocks = response.css("div.cb-col.cb-col-100.cb-plyr-tbody")
            current_series = ""
            for block in content_blocks:
                series_header = block.css("h2.cb-lv-grn-strip::text").get("")
                if series_header:
                    current_series = series_header.strip()
                    continue
                match_cards = block.css("div.cb-mtch-lst.cb-col.cb-col-100")
                if not match_cards:
                    match_cards = block.css("div.cb-col-100.cb-col")
                for card in match_cards:
                    yield from self._parse_match_card(card, current_series)

    def _parse_match_card(self, card, series_name: str):
        """Extract match data from a Cricbuzz match card element.

        Args:
            card: Scrapy Selector for the match card.
            series_name: Name of the series this match belongs to.

        Yields:
            MatchItem if sufficient data is extracted.
        """
        import re

        # --- Teams ---
        team_elements = card.xpath(".//span[contains(@class, 'wb:block')]/text()").getall()
        if len(team_elements) < 2:
            team_elements = card.css("div.cb-hmscg-tm-name::text").getall()
        if len(team_elements) < 2:
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
        result = card.xpath("./span/text()").get("").strip()
        if not result:
            result = card.css("div.cb-text-complete::text").get("").strip()
        if not result:
            result = card.css("a.cb-text-complete::text").get("").strip()
        if not result:
            result = card.css("div.cb-lv-scrs-well span.cb-text-complete::text").get("").strip()

        # --- Venue ---
        venue = card.css("div:first-child span::text").get("").strip()
        if not venue:
            venue = card.css("div.text-gray span::text").get("").strip()
        if not venue:
            venue = card.css("span.cb-font-12.text-gray::text").get("").strip()

        # --- Date ---
        match_date = ""
        href = card.attrib.get("href", "")
        year_match = re.search(r'\b(202\d)\b', href)
        if year_match:
            match_date = year_match.group(1)
        else:
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
