-- Cricket Analytics Dashboard — Database Schema
-- SQLite-compatible DDL (easily portable to PostgreSQL)

CREATE TABLE IF NOT EXISTS players (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    country         TEXT,
    role            TEXT,
    batting_style   TEXT,
    bowling_style   TEXT,
    matches         INTEGER DEFAULT 0,
    runs            INTEGER DEFAULT 0,
    wickets         INTEGER DEFAULT 0,
    average         REAL DEFAULT 0.0,
    strike_rate     REAL DEFAULT 0.0,
    profile_url     TEXT UNIQUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teams (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    team_name       TEXT NOT NULL UNIQUE,
    country         TEXT,
    captain         TEXT,
    coach           TEXT,
    ranking         INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS series (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    host            TEXT,
    start_date      TEXT,
    end_date        TEXT,
    winner          TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, start_date)
);

CREATE TABLE IF NOT EXISTS matches (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    series          TEXT,
    team1           TEXT,
    team2           TEXT,
    date            TEXT,
    venue           TEXT,
    result          TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team1, team2, date, venue)
);

-- Indexes for fast dashboard queries
CREATE INDEX IF NOT EXISTS idx_players_country ON players(country);
CREATE INDEX IF NOT EXISTS idx_players_role ON players(role);
CREATE INDEX IF NOT EXISTS idx_players_name ON players(name);
CREATE INDEX IF NOT EXISTS idx_teams_team_name ON teams(team_name);
CREATE INDEX IF NOT EXISTS idx_matches_series ON matches(series);
CREATE INDEX IF NOT EXISTS idx_matches_team1 ON matches(team1);
CREATE INDEX IF NOT EXISTS idx_matches_team2 ON matches(team2);
CREATE INDEX IF NOT EXISTS idx_series_name ON series(name);
