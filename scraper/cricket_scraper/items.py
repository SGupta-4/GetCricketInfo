"""
Scrapy Item definitions for the Cricket Analytics Dashboard.

Each Item class maps directly to a database table.
"""

import scrapy


class PlayerItem(scrapy.Item):
    """Represents a cricket player."""
    name = scrapy.Field()
    country = scrapy.Field()
    role = scrapy.Field()
    batting_style = scrapy.Field()
    bowling_style = scrapy.Field()
    matches = scrapy.Field()
    runs = scrapy.Field()
    wickets = scrapy.Field()
    average = scrapy.Field()
    strike_rate = scrapy.Field()
    profile_url = scrapy.Field()


class TeamItem(scrapy.Item):
    """Represents a cricket team."""
    team_name = scrapy.Field()
    country = scrapy.Field()
    captain = scrapy.Field()
    coach = scrapy.Field()
    ranking = scrapy.Field()


class SeriesItem(scrapy.Item):
    """Represents a cricket series or tournament."""
    name = scrapy.Field()
    host = scrapy.Field()
    start_date = scrapy.Field()
    end_date = scrapy.Field()
    winner = scrapy.Field()


class MatchItem(scrapy.Item):
    """Represents a cricket match."""
    series = scrapy.Field()
    team1 = scrapy.Field()
    team2 = scrapy.Field()
    date = scrapy.Field()
    venue = scrapy.Field()
    result = scrapy.Field()
