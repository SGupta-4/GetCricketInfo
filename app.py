"""
Cricket Analytics Dashboard — Streamlit Application

A professional, production-quality cricket analytics dashboard with:
- Overview metrics
- Player search, filtering, profiles, and comparison
- Team information
- Series/Tournament browser
- Match results with filters
- ICC Rankings view
- Data refresh via subprocess

Performance: uses @st.cache_data, LIMIT queries, and lazy loading.
Optimized for AWS Free Tier (1 GB RAM).
"""

import os
import sys
import subprocess
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Path setup — ensure the database module is importable
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from database.db_manager import CricketDB

# ---------------------------------------------------------------------------
# Streamlit page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Cricket Analytics Dashboard",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for premium look
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: transform 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }
    div[data-testid="stMetric"] label {
        color: #a8d4f7 !important;
        font-weight: 600;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: white !important;
        font-size: 2.2rem !important;
        font-weight: 700;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f1b2d 0%, #1a2942 100%);
    }
    section[data-testid="stSidebar"] .stRadio label {
        color: #e0e8f0 !important;
        font-weight: 500;
    }

    /* Headers */
    h1 { color: #1e3a5f; border-bottom: 3px solid #2d5a87; padding-bottom: 10px; }
    h2, h3 { color: #2d5a87; }

    /* Tables */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #2d5a87, #1e3a5f);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #3a6f9e, #2d5a87);
        box-shadow: 0 4px 12px rgba(45,90,135,0.3);
        transform: translateY(-1px);
    }

    /* Cards */
    .player-card {
        background: linear-gradient(135deg, #f8fafc, #e8f0fe);
        border-radius: 12px;
        padding: 20px;
        border-left: 4px solid #2d5a87;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .info-box {
        background: linear-gradient(135deg, #e3f2fd, #bbdefb);
        padding: 16px 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Database initialisation
# ---------------------------------------------------------------------------
@st.cache_resource
def get_db() -> CricketDB:
    """Create and initialise the database connection (cached)."""
    db_instance = CricketDB()
    db_instance.init_db()
    return db_instance

db = get_db()


# ---------------------------------------------------------------------------
# Cached data loading helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def load_counts() -> dict:
    return db.get_counts()

@st.cache_data(ttl=300)
def load_players(country=None, role=None, search=None) -> pd.DataFrame:
    rows = db.get_players(country=country, role=role, search=search)
    return pd.DataFrame(rows) if rows else pd.DataFrame()

@st.cache_data(ttl=300)
def load_player_names() -> list:
    return db.get_player_names()

@st.cache_data(ttl=300)
def load_teams() -> pd.DataFrame:
    rows = db.get_teams()
    return pd.DataFrame(rows) if rows else pd.DataFrame()

@st.cache_data(ttl=300)
def load_series() -> pd.DataFrame:
    rows = db.get_series()
    return pd.DataFrame(rows) if rows else pd.DataFrame()

@st.cache_data(ttl=300)
def load_matches(team=None, series=None) -> pd.DataFrame:
    rows = db.get_matches(team=team, series=series)
    return pd.DataFrame(rows) if rows else pd.DataFrame()

@st.cache_data(ttl=300)
def load_countries() -> list:
    return db.get_distinct_countries()

@st.cache_data(ttl=300)
def load_roles() -> list:
    return db.get_distinct_roles()

@st.cache_data(ttl=300)
def load_team_names() -> list:
    return db.get_team_names()

@st.cache_data(ttl=300)
def load_series_names() -> list:
    return db.get_series_names()


# ---------------------------------------------------------------------------
# Refresh handler
# ---------------------------------------------------------------------------

def _run_refresh():
    """Run Scrapy spiders via subprocess and show progress."""
    scraper_dir = os.path.join(_PROJECT_ROOT, "scraper")
    spiders = ["teams", "players", "series", "matches"]
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, spider_name in enumerate(spiders):
        status_text.markdown(f"🔄 Running **{spider_name}** spider...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "scrapy", "crawl", spider_name],
                cwd=scraper_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                st.warning(f"⚠️ {spider_name}: {result.stderr[:200]}")
            else:
                st.success(f"✅ {spider_name} completed")
        except subprocess.TimeoutExpired:
            st.warning(f"⏰ {spider_name} timed out (5 min)")
        except Exception as e:
            st.error(f"❌ {spider_name}: {e}")
        progress_bar.progress((i + 1) / len(spiders))

    status_text.markdown("✅ **All spiders finished!**")
    st.session_state["refresh_triggered"] = False
    st.cache_data.clear()


# ===========================================================================
# PAGE FUNCTIONS
# ===========================================================================

def page_overview():
    """Display overview metrics and summary statistics."""
    st.markdown("# 📊 Cricket Analytics Overview")
    st.markdown("---")

    counts = load_counts()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Players", f"{counts.get('players', 0):,}")
    with col2:
        st.metric("Total Teams", f"{counts.get('teams', 0):,}")
    with col3:
        st.metric("Total Matches", f"{counts.get('matches', 0):,}")
    with col4:
        st.metric("Total Series", f"{counts.get('series', 0):,}")

    st.markdown("---")

    col_left, col_right = st.columns(2)
    players_df = load_players()

    with col_left:
        st.markdown("### 🌍 Players by Country")
        if not players_df.empty and "country" in players_df.columns:
            country_counts = players_df["country"].value_counts().head(10)
            st.bar_chart(country_counts)
        else:
            st.info("No player data available. Click **Update Cricket Data** in the sidebar.")

    with col_right:
        st.markdown("### 🏏 Players by Role")
        if not players_df.empty and "role" in players_df.columns:
            role_counts = players_df["role"].value_counts()
            st.bar_chart(role_counts)
        else:
            st.info("No player data available.")


def page_players():
    """Display player search, filters, profiles, and comparison tool."""
    st.markdown("# 🧑 Player Analytics")
    st.markdown("---")

    # Filters
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        countries = ["All"] + load_countries()
        selected_country = st.selectbox("🌍 Country", countries, key="player_country")
    with filter_col2:
        roles = ["All"] + load_roles()
        selected_role = st.selectbox("🎯 Role", roles, key="player_role")
    with filter_col3:
        player_names = load_player_names()
        search_query = st.selectbox(
            "🔍 Search Player",
            options=[""] + player_names,
            key="player_search",
            placeholder="Type to search...",
        )

    country_filter = selected_country if selected_country != "All" else None
    role_filter = selected_role if selected_role != "All" else None
    search_filter = search_query if search_query else None

    players_df = load_players(country=country_filter, role=role_filter, search=search_filter)

    if players_df.empty:
        st.info("No players found. Try adjusting filters or update data from the sidebar.")
        return

    # Sortable table
    st.markdown("### 📋 Player Directory")
    display_cols = ["name", "country", "role", "matches", "runs", "wickets", "average", "strike_rate"]
    avail = [c for c in display_cols if c in players_df.columns]
    st.dataframe(players_df[avail], use_container_width=True, hide_index=True, height=400)

    st.markdown("---")

    # Player profile
    st.markdown("### 👤 Player Profile")
    name_list = players_df["name"].tolist() if "name" in players_df.columns else []
    if name_list:
        sel = st.selectbox("Select a player", name_list, key="player_profile")
        if sel:
            p_row = players_df[players_df["name"] == sel]
            if not p_row.empty:
                p = p_row.iloc[0]
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"""<div class="player-card">
                        <h3>🏏 {p.get('name','N/A')}</h3>
                        <p><b>Country:</b> {p.get('country','N/A')}</p>
                        <p><b>Role:</b> {p.get('role','N/A')}</p>
                        <p><b>Batting Style:</b> {p.get('batting_style','N/A')}</p>
                        <p><b>Bowling Style:</b> {p.get('bowling_style','N/A')}</p>
                    </div>""", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""<div class="player-card">
                        <h3>📊 Career Statistics</h3>
                        <p><b>Matches:</b> {p.get('matches',0):,}</p>
                        <p><b>Runs:</b> {p.get('runs',0):,}</p>
                        <p><b>Wickets:</b> {p.get('wickets',0):,}</p>
                        <p><b>Average:</b> {p.get('average',0):.2f}</p>
                        <p><b>Strike Rate:</b> {p.get('strike_rate',0):.2f}</p>
                    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Player comparison
    st.markdown("### ⚖️ Player Comparison Tool")
    if len(players_df) >= 2 and "name" in players_df.columns:
        pl = players_df["name"].tolist()
        cc1, cc2 = st.columns(2)
        with cc1:
            player_a = st.selectbox("Player 1", pl, key="comp_a")
        with cc2:
            player_b = st.selectbox("Player 2", [x for x in pl if x != player_a] or pl, key="comp_b")

        if player_a and player_b and player_a != player_b:
            ra = players_df[players_df["name"] == player_a].iloc[0]
            rb = players_df[players_df["name"] == player_b].iloc[0]

            comp_data = {
                "Stat": ["Country", "Role", "Matches", "Runs", "Wickets", "Average", "Strike Rate"],
                player_a: [ra.get("country",""), ra.get("role",""), ra.get("matches",0),
                           ra.get("runs",0), ra.get("wickets",0),
                           f"{ra.get('average',0):.2f}", f"{ra.get('strike_rate',0):.2f}"],
                player_b: [rb.get("country",""), rb.get("role",""), rb.get("matches",0),
                           rb.get("runs",0), rb.get("wickets",0),
                           f"{rb.get('average',0):.2f}", f"{rb.get('strike_rate',0):.2f}"],
            }
            st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

            st.markdown("#### 📊 Visual Comparison")
            vc1, vc2 = st.columns(2)
            with vc1:
                st.markdown("**Runs**")
                st.bar_chart(pd.DataFrame({"Runs": [ra.get("runs",0), rb.get("runs",0)]},
                                          index=[player_a, player_b]))
            with vc2:
                st.markdown("**Wickets**")
                st.bar_chart(pd.DataFrame({"Wickets": [ra.get("wickets",0), rb.get("wickets",0)]},
                                          index=[player_a, player_b]))
    else:
        st.info("Need at least 2 players in the database for comparison.")


def page_teams():
    """Display team details."""
    st.markdown("# 🏴 Team Analytics")
    st.markdown("---")

    teams_df = load_teams()
    if teams_df.empty:
        st.info("No team data available. Click **Update Cricket Data** in the sidebar.")
        return

    team_names = teams_df["team_name"].tolist() if "team_name" in teams_df.columns else []
    selected_team = st.selectbox("Select Team", team_names, key="team_select")

    if selected_team:
        t_row = teams_df[teams_df["team_name"] == selected_team]
        if not t_row.empty:
            t = t_row.iloc[0]
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("🏆 Ranking", f"#{t.get('ranking','N/A')}")
            with c2:
                st.metric("👨‍✈️ Captain", t.get("captain","N/A") or "N/A")
            with c3:
                st.metric("🧑‍🏫 Coach", t.get("coach","N/A") or "N/A")

    st.markdown("---")
    st.markdown("### 📋 All Teams")
    dcols = ["team_name", "country", "captain", "coach", "ranking"]
    acols = [c for c in dcols if c in teams_df.columns]
    st.dataframe(teams_df[acols], use_container_width=True, hide_index=True)


def page_series():
    """Display series/tournament information."""
    st.markdown("# 🏆 Series & Tournaments")
    st.markdown("---")

    series_df = load_series()
    if series_df.empty:
        st.info("No series data available. Click **Update Cricket Data** in the sidebar.")
        return

    st.markdown("### 📋 All Series")
    dcols = ["name", "host", "start_date", "end_date", "winner"]
    acols = [c for c in dcols if c in series_df.columns]
    st.dataframe(series_df[acols], use_container_width=True, hide_index=True, height=400)

    st.markdown("---")
    st.markdown("### 📖 Series Details")
    snames = series_df["name"].tolist() if "name" in series_df.columns else []
    sel_s = st.selectbox("Select a series", snames, key="series_detail")

    if sel_s:
        s_row = series_df[series_df["name"] == sel_s]
        if not s_row.empty:
            s = s_row.iloc[0]
            sc1, sc2 = st.columns(2)
            with sc1:
                st.markdown(f"""<div class="info-box">
                    <h4>📅 Schedule</h4>
                    <p><b>Start:</b> {s.get('start_date','N/A')}</p>
                    <p><b>End:</b> {s.get('end_date','N/A')}</p>
                    <p><b>Host:</b> {s.get('host','N/A')}</p>
                </div>""", unsafe_allow_html=True)
            with sc2:
                st.markdown(f"""<div class="info-box">
                    <h4>🏆 Result</h4>
                    <p><b>Winner:</b> {s.get('winner','TBD') or 'TBD'}</p>
                </div>""", unsafe_allow_html=True)

            matches_in = load_matches(series=sel_s)
            if not matches_in.empty:
                st.markdown("#### ⚔️ Matches in this Series")
                mcols = ["team1", "team2", "date", "venue", "result"]
                macols = [c for c in mcols if c in matches_in.columns]
                st.dataframe(matches_in[macols], use_container_width=True, hide_index=True)


def page_matches():
    """Display match results with filters."""
    st.markdown("# ⚔️ Match Results")
    st.markdown("---")

    fc1, fc2 = st.columns(2)
    with fc1:
        t_opts = ["All"] + load_team_names()
        sel_t = st.selectbox("🏴 Filter by Team", t_opts, key="match_team")
    with fc2:
        s_opts = ["All"] + load_series_names()
        sel_s = st.selectbox("🏆 Filter by Series", s_opts, key="match_series")

    tf = sel_t if sel_t != "All" else None
    sf = sel_s if sel_s != "All" else None

    matches_df = load_matches(team=tf, series=sf)
    if matches_df.empty:
        st.info("No match data found. Try adjusting filters or update data from the sidebar.")
        return

    st.markdown(f"### 📋 Showing {len(matches_df)} matches")
    dcols = ["series", "team1", "team2", "date", "venue", "result"]
    acols = [c for c in dcols if c in matches_df.columns]
    st.dataframe(matches_df[acols], use_container_width=True, hide_index=True, height=500)


def page_rankings():
    """Display player and team rankings."""
    st.markdown("# 📈 Cricket Rankings")
    st.markdown("---")

    tab_p, tab_t = st.tabs(["🧑 Player Rankings", "🏴 Team Rankings"])

    with tab_p:
        players_df = load_players()

        st.markdown("### Top Players by Runs")
        if not players_df.empty and "runs" in players_df.columns:
            top_bat = players_df.nlargest(20, "runs")
            dcols = ["name", "country", "matches", "runs", "average", "strike_rate"]
            acols = [c for c in dcols if c in top_bat.columns]
            st.dataframe(top_bat[acols].reset_index(drop=True), use_container_width=True, hide_index=True)

            st.markdown("#### 📊 Top 10 Run Scorers")
            top10 = players_df.nlargest(10, "runs")
            st.bar_chart(top10.set_index("name")[["runs"]])
        else:
            st.info("No player data available.")

        st.markdown("---")
        st.markdown("### Top Players by Wickets")
        if not players_df.empty and "wickets" in players_df.columns:
            top_bowl = players_df.nlargest(20, "wickets")
            dcols = ["name", "country", "matches", "wickets"]
            acols = [c for c in dcols if c in top_bowl.columns]
            st.dataframe(top_bowl[acols].reset_index(drop=True), use_container_width=True, hide_index=True)

            st.markdown("#### 📊 Top 10 Wicket Takers")
            top10w = players_df.nlargest(10, "wickets")
            st.bar_chart(top10w.set_index("name")[["wickets"]])
        else:
            st.info("No player data available.")

    with tab_t:
        st.markdown("### Team Rankings")
        teams_df = load_teams()
        if not teams_df.empty:
            dcols = ["ranking", "team_name", "captain", "coach"]
            acols = [c for c in dcols if c in teams_df.columns]
            st.dataframe(teams_df[acols], use_container_width=True, hide_index=True)
        else:
            st.info("No team data available.")


# ===========================================================================
# Sidebar navigation & page routing
# ===========================================================================

with st.sidebar:
    st.markdown("## 🏏 Cricket Analytics")
    st.markdown("---")
    page = st.radio(
        "Navigation",
        options=[
            "📊 Overview",
            "🧑 Players",
            "🏴 Teams",
            "🏆 Series",
            "⚔️ Matches",
            "📈 Rankings",
        ],
        label_visibility="collapsed",
    )
    st.markdown("---")

    # Refresh data button
    st.markdown("### 🔄 Data Management")
    if st.button("Update Cricket Data", use_container_width=True):
        st.session_state["refresh_triggered"] = True

    if st.session_state.get("refresh_triggered"):
        _run_refresh()

    st.markdown("---")
    st.caption("Cricket Analytics Dashboard v1.0")
    st.caption("Powered by Scrapy + Streamlit")

# Run the selected page
_PAGES = {
    "📊 Overview": page_overview,
    "🧑 Players": page_players,
    "🏴 Teams": page_teams,
    "🏆 Series": page_series,
    "⚔️ Matches": page_matches,
    "📈 Rankings": page_rankings,
}
page_fn = _PAGES.get(page)
if page_fn:
    page_fn()
