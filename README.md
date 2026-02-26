# 🏏 Cricket Analytics Dashboard

A production-quality cricket analytics platform that scrapes live cricket data and displays structured analytics through an interactive Streamlit dashboard. Optimized for **AWS Free Tier** deployment.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Scrapy](https://img.shields.io/badge/Scrapy-2.11+-green?logo=scrapy)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red?logo=streamlit)
![SQLite](https://img.shields.io/badge/SQLite-3-blue?logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Features

### 📊 Dashboard Pages
| Page | Description |
|------|-------------|
| **Overview** | Metric cards (total players, teams, matches, series) + distribution charts |
| **Players** | Search, filter by country/role, sortable table, player profile panel |
| **Teams** | Team selector with ranking, captain, and coach display |
| **Series** | Series browser with date, host, winner details + linked matches |
| **Matches** | Filter by team/series, full match result table |
| **Rankings** | Top run-scorers & wicket-takers with bar charts, team rankings |

### 🔧 Advanced Features
- ⚖️ **Player Comparison Tool** — side-by-side stats with visual bar charts
- 🔍 **Smart Search** — autocomplete player names via dropdown
- 🔄 **Live Data Refresh** — run all Scrapy spiders from the dashboard with one click
- 📈 **Charts** — runs distribution, wickets distribution, country breakdown
- ⚡ **Performance** — `@st.cache_data`, `LIMIT` queries, lazy loading, SQLite WAL mode

---

## 🏗️ Architecture

```
cricket_dashboard/
├── app.py                          # Streamlit dashboard (6 pages)
├── requirements.txt                # Minimal dependencies
├── DEPLOYMENT.md                   # AWS Free Tier deployment guide
├── database/
│   ├── schema.sql                  # DDL with indexes
│   ├── db_manager.py               # CricketDB class (upsert + query)
│   └── cricket.db                  # Auto-created at runtime
└── scraper/
    ├── scrapy.cfg
    └── cricket_scraper/
        ├── items.py                # PlayerItem, TeamItem, SeriesItem, MatchItem
        ├── settings.py             # Polite crawling, auto-throttle
        ├── middlewares.py          # User-Agent rotation (8 browsers)
        ├── pipelines.py            # Data cleaning → SQLite (no JSON files)
        └── spiders/
            ├── player_spider.py    # 12 international teams
            ├── team_spider.py      # Team overview pages
            ├── series_spider.py    # International + league series
            └── match_spider.py     # Recent + upcoming matches
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+

### Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/cricket-analytics-dashboard.git
cd cricket-analytics-dashboard

# Install dependencies
pip install -r requirements.txt
```

### Run Scrapers (Initial Data Load)

```bash
cd scraper

# Scrape team info, player profiles, series, and matches
scrapy crawl teams
scrapy crawl players
scrapy crawl series
scrapy crawl matches

cd ..
```

> Each spider respects a 2–3 second delay. Full crawl takes ~10–15 minutes.

### Launch Dashboard

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 🗃️ Database Schema

| Table | Key Columns | Unique Constraint |
|-------|-------------|-------------------|
| `players` | name, country, role, matches, runs, wickets, average, strike_rate | `profile_url` |
| `teams` | team_name, captain, coach, ranking | `team_name` |
| `series` | name, host, start_date, end_date, winner | `(name, start_date)` |
| `matches` | series, team1, team2, date, venue, result | `(team1, team2, date, venue)` |

All queries use **parameterized statements** (SQL injection safe). Schema is portable to PostgreSQL.

---

## 🕷️ Scraping Configuration

| Setting | Value |
|---------|-------|
| `DOWNLOAD_DELAY` | 2 seconds |
| `AUTOTHROTTLE_ENABLED` | True |
| `CONCURRENT_REQUESTS` | 4 |
| `RETRY_TIMES` | 3 |
| `ROBOTSTXT_OBEY` | False |
| User-Agent Rotation | 8 browser UAs |

Data flows **Scrapy → Pipeline → SQLite** with no intermediate JSON files.

---

## ☁️ AWS Free Tier Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step instructions covering:

- EC2 t2.micro setup (1 vCPU, 1 GB RAM)
- Virtual environment + pip install
- systemd service for auto-start
- Cron job for daily data refresh
- Swap file for memory safety

**Resource footprint:** < 500 MB RAM, < 10 MB disk (DB + app).

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Scraping | Scrapy 2.11+ |
| Backend | Python 3.10+ |
| Frontend | Streamlit 1.30+ |
| Database | SQLite 3 (PostgreSQL upgradeable) |
| Data Processing | Pandas |
| HTML Parsing | BeautifulSoup4, lxml |

---

## 🔒 Security

- ✅ Parameterized SQL queries (no string formatting)
- ✅ Input validation on all user-facing filters
- ✅ No secrets or credentials in code
- ✅ Rate-limited scraping with delays

---

## 📝 License

This project is licensed under the MIT License.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
