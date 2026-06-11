-- =============================================================================
-- NBA Player Financial Value Pipeline
-- schema.sql
-- Run this in the Supabase SQL editor to initialize or reset all tables.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- RAW TABLES (populated by ingest.py)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS advanced_stats (
    id          SERIAL PRIMARY KEY,
    player      TEXT    NOT NULL,
    player_id   TEXT,                   -- BBREF player ID e.g. curryst01
    bpm         NUMERIC,                -- Box Plus/Minus
    vorp        NUMERIC,                -- Value Over Replacement Player
    per         NUMERIC,                -- Player Efficiency Rating
    ws          NUMERIC,                -- Win Shares
    updated_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS salaries (
    id          SERIAL PRIMARY KEY,
    player      TEXT    NOT NULL,
    salary      NUMERIC,                -- 2025-26 salary in USD
    updated_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS minutes (
    id          SERIAL PRIMARY KEY,
    player_name TEXT    NOT NULL,
    min         NUMERIC,                -- minutes per game
    updated_at  TIMESTAMP DEFAULT NOW()
);

-- Game stats per game (traditional box score averages)
CREATE TABLE IF NOT EXISTS player_game_stats_per_game (
    id          SERIAL PRIMARY KEY,
    player      TEXT    NOT NULL,
    min         NUMERIC,                -- minutes per game
    pts         NUMERIC,                -- points per game
    reb         NUMERIC,                -- rebounds per game
    ast         NUMERIC,                -- assists per game
    fg3_pct     NUMERIC,                -- 3-point field goal percentage
    fg2_pct     NUMERIC,                -- 2-point field goal percentage (computed)
    ft_pct      NUMERIC,                -- free throw percentage
    updated_at  TIMESTAMP DEFAULT NOW()
);

-- Game stats per 36 minutes (normalizes for playing time)
CREATE TABLE IF NOT EXISTS player_game_stats_per_36 (
    id          SERIAL PRIMARY KEY,
    player      TEXT    NOT NULL,
    min         NUMERIC,                -- minutes per game (actual, not per 36)
    pts         NUMERIC,                -- points per 36 minutes
    reb         NUMERIC,                -- rebounds per 36 minutes
    ast         NUMERIC,                -- assists per 36 minutes
    fg3_pct     NUMERIC,                -- 3-point field goal percentage
    fg2_pct     NUMERIC,                -- 2-point field goal percentage (computed)
    ft_pct      NUMERIC,                -- free throw percentage
    updated_at  TIMESTAMP DEFAULT NOW()
);

-- Game stats per 100 possessions (pace-adjusted)
CREATE TABLE IF NOT EXISTS player_game_stats_per_100 (
    id          SERIAL PRIMARY KEY,
    player      TEXT    NOT NULL,
    min         NUMERIC,                -- minutes per game (actual, not per 100)
    pts         NUMERIC,                -- points per 100 possessions
    reb         NUMERIC,                -- rebounds per 100 possessions
    ast         NUMERIC,                -- assists per 100 possessions
    fg3_pct     NUMERIC,                -- 3-point field goal percentage
    fg2_pct     NUMERIC,                -- 2-point field goal percentage (computed)
    ft_pct      NUMERIC,                -- free throw percentage
    updated_at  TIMESTAMP DEFAULT NOW()
);


-- -----------------------------------------------------------------------------
-- TRANSFORMED TABLE (populated by transform.py)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS player_metrics (
    id                   SERIAL PRIMARY KEY,
    player               TEXT    NOT NULL,
    player_id            TEXT,                   -- BBREF player ID e.g. curryst01
    salary               NUMERIC,                -- 2025-26 salary in USD
    min                  NUMERIC,                -- minutes per game
    vorp                 NUMERIC,                -- Value Over Replacement Player
    bpm                  NUMERIC,                -- Box Plus/Minus
    per                  NUMERIC,                -- Player Efficiency Rating
    ws                   NUMERIC,                -- Win Shares
    vorp_per_dollar      NUMERIC,                -- VORP / salary
    ws_per_dollar        NUMERIC,                -- WS / salary
    vorp_per_dollar_rank INTEGER,                -- rank among all qualified players
    ws_per_dollar_rank   INTEGER,                -- rank among all qualified players
    overall_value_rank   INTEGER,                -- avg of vorp/$ and ws/$ ranks, re-ranked
    updated_at           TIMESTAMP DEFAULT NOW()
);


-- -----------------------------------------------------------------------------
-- NOTES
-- -----------------------------------------------------------------------------
-- Qualified players: minimum 10 minutes per game (filtered in transform.py)
-- Ranks: 1 = best value. overall_value_rank averages vorp_per_dollar_rank
--        and ws_per_dollar_rank, then re-ranks that average.
-- 2P% is computed as (FG - 3P) / (FGA - 3PA) since BBREF does not provide it directly.
-- Per 100 possessions page does not include minutes — min will be NULL for that table.
-- Headshots: https://www.basketball-reference.com/req/202106291/images/headshots/{player_id}.jpg
-- -----------------------------------------------------------------------------


-- -----------------------------------------------------------------------------
-- ROW LEVEL SECURITY
-- -----------------------------------------------------------------------------
-- RLS is enabled on all tables. Public read is allowed since all data is
-- publicly available NBA stats. Write operations are restricted to the
-- direct database connection used by ingest.py and transform.py.
-- -----------------------------------------------------------------------------
ALTER TABLE advanced_stats            ENABLE ROW LEVEL SECURITY;
ALTER TABLE salaries                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE minutes                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_metrics            ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_game_stats         ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_game_stats_per_game ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_game_stats_per_36  ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_game_stats_per_100 ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow public read" ON advanced_stats            FOR SELECT USING (true);
CREATE POLICY "allow public read" ON salaries                  FOR SELECT USING (true);
CREATE POLICY "allow public read" ON minutes                   FOR SELECT USING (true);
CREATE POLICY "allow public read" ON player_metrics            FOR SELECT USING (true);
CREATE POLICY "allow public read" ON player_game_stats         FOR SELECT USING (true);
CREATE POLICY "allow public read" ON player_game_stats_per_game FOR SELECT USING (true);
CREATE POLICY "allow public read" ON player_game_stats_per_36  FOR SELECT USING (true);
CREATE POLICY "allow public read" ON player_game_stats_per_100 FOR SELECT USING (true);