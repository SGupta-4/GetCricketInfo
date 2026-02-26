"""
Player Spider — Scrapes cricket player profiles and career statistics.

Primary target: Cricbuzz player profiles
Secondary target: ESPN Cricinfo player pages

The spider starts from team squad pages, follows links to individual
player profiles, and extracts biographical and career data.
"""

import scrapy
from cricket_scraper.items import PlayerItem


class PlayerSpider(scrapy.Spider):
    """Crawl player profiles from cricket websites."""

    name = "players"
    allowed_domains = ["www.cricbuzz.com", "www.espncricinfo.com"]

    # Start URLs: Cricbuzz team pages for major international teams
    # Each page lists the squad with links to individual player profiles
    _CRICBUZZ_TEAMS = [
        "https://www.cricbuzz.com/cricket-team/india/2/players",
        "https://www.cricbuzz.com/cricket-team/australia/4/players",
        "https://www.cricbuzz.com/cricket-team/england/9/players",
        "https://www.cricbuzz.com/cricket-team/south-africa/11/players",
        "https://www.cricbuzz.com/cricket-team/new-zealand/13/players",
        "https://www.cricbuzz.com/cricket-team/pakistan/3/players",
        "https://www.cricbuzz.com/cricket-team/sri-lanka/5/players",
        "https://www.cricbuzz.com/cricket-team/west-indies/6/players",
        "https://www.cricbuzz.com/cricket-team/bangladesh/7/players",
        "https://www.cricbuzz.com/cricket-team/afghanistan/96/players",
        "https://www.cricbuzz.com/cricket-team/zimbabwe/12/players",
        "https://www.cricbuzz.com/cricket-team/ireland/27/players",
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    }

    def start_requests(self):
        """Generate requests for each team's player listing page."""
        for url in self._CRICBUZZ_TEAMS:
            yield scrapy.Request(
                url=url,
                callback=self.parse_team_squad,
                errback=self.handle_error,
                meta={"dont_redirect": False},
            )

    def parse_team_squad(self, response):
        """Parse a team squad page and follow links to player profiles.

        Cricbuzz squad pages list players under category headers
        (Batters, All-Rounders, Bowlers, Wicket-Keepers).
        Each player name is a link to their profile.
        """
        self.logger.info("Parsing squad page: %s (status %s)", response.url, response.status)

        # Extract country from the URL path (e.g., /cricket-team/india/2/players → India)
        url_parts = response.url.split("/")
        country = ""
        for i, part in enumerate(url_parts):
            if part == "cricket-team" and i + 1 < len(url_parts):
                country = url_parts[i + 1].replace("-", " ").title()
                break

        # Find all player links on the squad page
        # Cricbuzz uses anchor tags with href pattern: /profiles/<id>/<player-name>
        player_links = response.css('a[href*="/profiles/"]')

        if not player_links:
            # Fallback: try broader selectors
            player_links = response.css('a[href*="/cricket-player/"]')

        for link in player_links:
            href = link.attrib.get("href", "")
            player_name = link.css("::text").get("").strip()

            if href and player_name:
                full_url = response.urljoin(href)
                yield scrapy.Request(
                    url=full_url,
                    callback=self.parse_player_profile,
                    errback=self.handle_error,
                    meta={"country": country, "player_name": player_name},
                )

    def parse_player_profile(self, response):
        """Parse an individual player profile page.

        Extracts personal info (role, batting/bowling style) and
        career statistics (matches, runs, wickets, average, strike rate).
        """
        self.logger.info("Parsing player profile: %s", response.url)

        country = response.meta.get("country", "")
        player_name = response.meta.get("player_name", "")

        # Try to extract the player name from the page if not in meta
        if not player_name:
            player_name = (
                response.css("h1.cb-font-40::text").get("")
                or response.css("h1::text").get("")
            ).strip()

        # --- Personal Info ---
        # Cricbuzz profiles show personal info in a structured list
        personal_info = {}
        info_items = response.css("div.cb-col.cb-col-60.cb-lst-itm-sm")
        info_labels = response.css("div.cb-col.cb-col-40.cb-lst-itm-sm")

        for label_el, value_el in zip(info_labels, info_items):
            label = label_el.css("::text").get("").strip().lower()
            value = value_el.css("::text").get("").strip()
            personal_info[label] = value

        # Extract specific fields
        role = personal_info.get("role", "")
        batting_style = personal_info.get("batting style", "")
        bowling_style = personal_info.get("bowling style", "")

        # Fallback: look for common CSS patterns
        if not role:
            role = response.css('div.cb-col.cb-col-60:contains("Role") + div::text').get("") or ""
        if not batting_style:
            batting_style = response.css('div.cb-col.cb-col-60:contains("Batting") + div::text').get("") or ""

        # --- Career Statistics ---
        # Cricbuzz shows career stats in table rows
        matches = 0
        runs = 0
        wickets = 0
        average = 0.0
        strike_rate = 0.0

        # Look for the career statistics table
        stat_tables = response.css("table.table.cb-col-100.cb-plyr-thead")
        if stat_tables:
            # Get the first table (usually overall career stats)
            for table in stat_tables:
                rows = table.css("tr")
                for row in rows:
                    cols = row.css("td::text").getall()
                    if len(cols) >= 5:
                        # Typical order: Format, Mat, Inn, Runs, ...
                        try:
                            matches += self._safe_int(cols[1])
                            runs += self._safe_int(cols[3])
                        except (IndexError, ValueError):
                            pass

        # Fallback: try extracting from stat value elements
        if matches == 0:
            stat_values = response.css("div.cb-plyr-stts div.cb-col-50::text").getall()
            if len(stat_values) >= 4:
                matches = self._safe_int(stat_values[0])
                runs = self._safe_int(stat_values[1])

        # Try to get wickets from bowling stats
        bowling_rows = response.css("table.cb-plyr-bowl-tbl tr")
        for row in bowling_rows:
            cols = row.css("td::text").getall()
            if len(cols) >= 5:
                try:
                    wickets += self._safe_int(cols[4])
                except (IndexError, ValueError):
                    pass

        yield PlayerItem(
            name=player_name,
            country=country,
            role=role,
            batting_style=batting_style,
            bowling_style=bowling_style,
            matches=matches,
            runs=runs,
            wickets=wickets,
            average=average,
            strike_rate=strike_rate,
            profile_url=response.url,
        )

    def handle_error(self, failure):
        """Log request failures without crashing the spider."""
        self.logger.error("Request failed: %s — %s", failure.request.url, failure.value)

    @staticmethod
    def _safe_int(value) -> int:
        """Convert a string to int, returning 0 on failure."""
        try:
            return int(str(value).replace(",", "").replace("-", "0").strip() or 0)
        except (ValueError, TypeError):
            return 0
