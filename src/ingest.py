import pandas as pd
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
from datetime import datetime

load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"))

# ── helpers ──────────────────────────────────────────────────────────────────

def upsert(df: pd.DataFrame, table: str, conflict_column: str):
    """
    Clears the table and reloads fresh data on each run.
    Simple and safe for a daily pipeline.
    """
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {table}"))
    df.to_sql(table, engine, if_exists="append", index=False)
    print(f"✓ {table}: {len(df)} rows written")

def get_current_nba_season_year(date_obj=None):
    if date_obj is None:
        date_obj = datetime.now()
        
    # The NBA season typically starts in October (Month 10).
    # If we are in October, November, or December, the season 
    # wraps up in the *following* calendar year.
    if date_obj.month >= 10:
        return date_obj.year + 1
    else:
        return date_obj.year

# ── fetch advanced stats ──────────────────────────────────────────────────────

def fetch_advanced_stats():
    url = f"https://www.basketball-reference.com/leagues/NBA_{CURRENT_YEAR}_advanced.html"

    req = Request(url, headers={"User-Agent": "python-urllib/3.11"})
    html = urlopen(req).read()
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "advanced"})

    def get_stat(tr, stat):
        td = tr.find("td", {"data-stat": stat})
        return td.text.strip() if td else None

    rows = []
    for tr in table.find("tbody").find_all("tr"):
        if "thead" in tr.get("class", []):
            continue
        td_player = tr.find("td", {"data-stat": "name_display"})
        if td_player is None:
            continue
        a_tag = td_player.find("a")
        if a_tag is None:
            continue

        # player_id is in data-append-csv attribute
        player_id = td_player.get("data-append-csv", "")

        rows.append({
            "player":    td_player.text.strip(),
            "player_id": player_id,
            "team":      get_stat(tr, "team_name_abbr"),
            "bpm":       get_stat(tr, "bpm"),
            "vorp":      get_stat(tr, "vorp"),
            "per":       get_stat(tr, "per"),
            "ws":        get_stat(tr, "ws"),
        })

    bbref = pd.DataFrame(rows)

    traded_players = bbref[bbref["team"].str.contains(r"\dTM", na=False)]["player"].unique()
    bbref_clean = bbref[
        (bbref["team"].str.contains(r"\dTM", na=False)) |
        (~bbref["player"].isin(traded_players))
    ].reset_index(drop=True)

    bbref_clean = bbref_clean[bbref_clean["player"] != "League Average"]
    bbref_clean = bbref_clean[["player", "player_id", "bpm", "vorp", "per", "ws"]].sort_values("player")

    for col in ["bpm", "vorp", "per", "ws"]:
        bbref_clean[col] = pd.to_numeric(bbref_clean[col], errors="coerce")

    bbref_clean.dropna(subset=["player"], inplace=True)
    return bbref_clean

# ── fetch salaries ────────────────────────────────────────────────────────────

def fetch_salaries():
    url = "https://www.basketball-reference.com/contracts/players.html"
    salary_df = pd.read_html(url)[0]

    salary_df.columns = salary_df.columns.droplevel(0)
    salary_df = salary_df[salary_df["Player"] != "Player"].copy()
    salary_df = (
        salary_df[["Player", "2025-26"]]
        .rename(columns={"Player": "player", "2025-26": "salary"})
    )
    salary_df["salary"] = pd.to_numeric(
        salary_df["salary"].str.replace(r"[$,]", "", regex=True), errors="coerce"
    )
    salary_df.dropna(inplace=True)
    salary_df.reset_index(drop=True, inplace=True)
    return salary_df

# ── fetch minutes ─────────────────────────────────────────────────────────────

def fetch_minutes():
    url = f"https://www.basketball-reference.com/leagues/NBA_{CURRENT_YEAR}_per_game.html"
    df = pd.read_html(url)[0]

    # Remove repeated header rows
    df = df[df["Player"] != "Player"].copy()

    traded_players = df[df.Team.str.contains(r"\dTM", na=False)]["Player"].unique()
    df_clean = df[
        (df.Team.str.contains(r"\dTM", na=False)) |
        (~df["Player"].isin(traded_players))
    ].reset_index(drop=True)

    df_clean = df_clean[["Player", "MP"]].rename(
        columns={"Player": "player_name", "MP": "min"}
    )
    df_clean["min"] = pd.to_numeric(df_clean["min"], errors="coerce")
    df_clean.dropna(inplace=True)
    return df_clean

# ── run pipeline ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting ingestion...")

    print(os.getenv("DATABASE_URL"))
    CURRENT_YEAR = get_current_nba_season_year()

    upsert(fetch_advanced_stats(), "advanced_stats", "player")
    upsert(fetch_salaries(),       "salaries",       "player")
    upsert(fetch_minutes(),        "minutes",        "player_name")

    print("Done ✓")