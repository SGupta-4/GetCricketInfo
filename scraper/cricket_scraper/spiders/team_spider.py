"""
Team Spider — Scrapes international cricket team information.

Primary target: Cricbuzz team pages
Secondary target: ESPN Cricinfo / ICC rankings

Extracts team name, country, captain, coach, and ICC ranking.
"""

import scrapy
from cricket_scraper.items import TeamItem


class TeamSpider(scrapy.Spider):
    """Crawl team information from cricket websites."""

    name = "teams"
    allowed_domains = ["www.cricbuzz.com", "www.espncricinfo.com", "www.icc-cricket.com"]

    # Cricbuzz team overview pages for all ICC Full Member + Associate teams
    _TEAM_URLS = [
        ("India", "https://www.cricbuzz.com/cricket-team/india/2"),
        ("Australia", "https://www.cricbuzz.com/cricket-team/australia/4"),
        ("England", "https://www.cricbuzz.com/cricket-team/england/9"),
        ("South Africa", "https://www.cricbuzz.com/cricket-team/south-africa/11"),
        ("New Zealand", "https://www.cricbuzz.com/cricket-team/new-zealand/13"),
        ("Pakistan", "https://www.cricbuzz.com/cricket-team/pakistan/3"),
        ("Sri Lanka", "https://www.cricbuzz.com/cricket-team/sri-lanka/5"),
        ("West Indies", "https://www.cricbuzz.com/cricket-team/west-indies/6"),
        ("Bangladesh", "https://www.cricbuzz.com/cricket-team/bangladesh/7"),
        ("Afghanistan", "https://www.cricbuzz.com/cricket-team/afghanistan/96"),
        ("Zimbabwe", "https://www.cricbuzz.com/cricket-team/zimbabwe/12"),
        ("Ireland", "https://www.cricbuzz.com/cricket-team/ireland/27"),
    ]

    # ICC Rankings page for team rankings
    _RANKINGS_URL = "https://www.icc-cricket.com/rankings/mens/team-rankings/test"

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    }

    def start_requests(self):
        """Generate requests for each team page."""
        for rank, (team_name, url) in enumerate(self._TEAM_URLS, start=1):
            yield scrapy.Request(
                url=url,
                callback=self.parse_team_page,
                errback=self.handle_error,
                meta={"team_name": team_name, "default_ranking": rank},
            )

    def parse_team_page(self, response):
        """Parse a Cricbuzz team overview page.

        Extracts captain, coach, and ranking information.
        """
        self.logger.info("Parsing team page: %s (status %s)", response.url, response.status)

        team_name = response.meta.get("team_name", "")
        default_ranking = response.meta.get("default_ranking", 0)

        # --- Extract team details ---
        # Cricbuzz team pages show details in info blocks
        captain = ""
        coach = ""
        ranking = default_ranking

        # Look for info items with label-value pairs
        info_labels = response.css("div.cb-team-info div.cb-col-40::text").getall()
        info_values = response.css("div.cb-team-info div.cb-col-60::text").getall()

        for label_raw, value in zip(info_labels, info_values):
            label = label_raw.strip().lower()
            value = value.strip()
            if "captain" in label:
                captain = value
            elif "coach" in label:
                coach = value
            elif "ranking" in label:
                try:
                    ranking = int(value)
                except (ValueError, TypeError):
                    pass

        # Fallback: broader selectors for captain and coach
        if not captain:
            captain = (
                response.xpath('//a[contains(translate(@title, "CAPTAIN", "captain"), "captain")]/text()').get("")
                or response.css('div.cb-font-16:contains("Captain") + div::text').get("")
            ).strip()

        if not coach:
            coach = (
                response.css('div.cb-font-16:contains("Coach") + div::text').get("")
            ).strip()

        yield TeamItem(
            team_name=team_name,
            country=team_name,
            captain=captain,
            coach=coach,
            ranking=ranking,
        )

    def handle_error(self, failure):
        """Log request failures without crashing."""
        self.logger.error("Request failed: %s — %s", failure.request.url, failure.value)
