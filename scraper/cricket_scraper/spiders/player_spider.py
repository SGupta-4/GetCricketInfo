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

        # --- Personal Info (NextJS Layout) ---
        personal_info = {}
        rows = response.xpath('//div[div[contains(@class, "w-1/3")] and div[contains(@class, "w-2/3")]]')
        for row in rows:
            label = row.xpath('./div[1]/text()').get("").strip().lower()
            value = row.xpath('./div[2]/text()').get("").strip()
            personal_info[label] = value

        role = personal_info.get("role", "")
        batting_style = personal_info.get("batting style", "")
        bowling_style = personal_info.get("bowling style", "")

        # Fallback to old Cricbuzz layout selectors
        if not role or not batting_style:
            old_info_items = response.css("div.cb-col.cb-col-60.cb-lst-itm-sm")
            old_info_labels = response.css("div.cb-col.cb-col-40.cb-lst-itm-sm")
            old_personal_info = {}
            for label_el, value_el in zip(old_info_labels, old_info_items):
                label = label_el.css("::text").get("").strip().lower()
                value = value_el.css("::text").get("").strip()
                old_personal_info[label] = value
            
            if not role:
                role = old_personal_info.get("role", "")
            if not batting_style:
                batting_style = old_personal_info.get("batting style", "")
            if not bowling_style:
                bowling_style = old_personal_info.get("bowling style", "")

        if not role:
            role = response.css('div.cb-col.cb-col-60:contains("Role") + div::text').get("") or ""
        if not batting_style:
            batting_style = response.css('div.cb-col.cb-col-60:contains("Batting") + div::text').get("") or ""

        # --- Career Statistics ---
        matches = 0
        runs = 0
        wickets = 0
        average = 0.0
        strike_rate = 0.0

        # NextJS Layout - Batting Career Summary
        batting_table = response.xpath('//*[contains(text(), "Batting Career Summary")]/following::table[1]')
        if batting_table:
            tb_rows = batting_table.xpath('.//tbody/tr')
            total_matches = 0
            total_innings = 0
            total_runs = 0
            total_balls = 0
            total_not_out = 0
            
            for row in tb_rows:
                cells = [c.strip() for c in row.xpath('.//td/text()').getall() if c.strip()]
                if not cells:
                    continue
                label = cells[0].lower()
                values = [self._safe_int(v) for v in cells[1:]]
                
                if "matches" in label:
                    total_matches = sum(values)
                elif "innings" in label:
                    total_innings = sum(values)
                elif "runs" in label:
                    total_runs = sum(values)
                elif "balls" in label:
                    total_balls = sum(values)
                elif "not out" in label:
                    total_not_out = sum(values)

            matches = total_matches
            runs = total_runs
            
            # Calculate batting average
            outs = total_innings - total_not_out
            if outs > 0:
                average = total_runs / outs
            elif total_innings > 0:
                average = float(total_runs)
                
            # Calculate batting strike rate
            if total_balls > 0:
                strike_rate = (total_runs / total_balls) * 100

        # NextJS Layout - Bowling Career Summary
        bowling_table = response.xpath('//*[contains(text(), "Bowling Career Summary")]/following::table[1]')
        if bowling_table:
            tb_rows = bowling_table.xpath('.//tbody/tr')
            total_wickets = 0
            for row in tb_rows:
                cells = [c.strip() for c in row.xpath('.//td/text()').getall() if c.strip()]
                if not cells:
                    continue
                label = cells[0].lower()
                values = [self._safe_int(v) for v in cells[1:]]
                if "wickets" in label:
                    total_wickets = sum(values)
            wickets = total_wickets

        # Fallback to old Cricbuzz layout selectors for stats
        if matches == 0 and wickets == 0:
            old_stat_tables = response.css("table.table.cb-col-100.cb-plyr-thead")
            if old_stat_tables:
                for table in old_stat_tables:
                    rows = table.css("tr")
                    for row in rows:
                        cols = row.css("td::text").getall()
                        if len(cols) >= 5:
                            try:
                                matches += self._safe_int(cols[1])
                                runs += self._safe_int(cols[3])
                            except (IndexError, ValueError):
                                pass

            if matches == 0:
                stat_values = response.css("div.cb-plyr-stts div.cb-col-50::text").getall()
                if len(stat_values) >= 4:
                    matches = self._safe_int(stat_values[0])
                    runs = self._safe_int(stat_values[1])

            old_bowling_rows = response.css("table.cb-plyr-bowl-tbl tr")
            for row in old_bowling_rows:
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
