import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# ── connection ────────────────────────────────────────────────────────────────

def get_engine():
    return create_engine(st.secrets["DATABASE_URL"])

@st.cache_data(ttl=3600)
def load_metrics():
    engine = get_engine()
    metrics       = pd.read_sql("SELECT * FROM player_metrics ORDER BY overall_value_rank", engine)
    stats_per_game = pd.read_sql("SELECT * FROM player_game_stats_per_game", engine)
    stats_per_36   = pd.read_sql("SELECT * FROM player_game_stats_per_36", engine)
    stats_per_100  = pd.read_sql("SELECT * FROM player_game_stats_per_100", engine)
    return metrics, stats_per_game, stats_per_36, stats_per_100

# @st.cache_data(ttl=3600)
# def load_metrics():
#     engine = get_engine()
#     return pd.read_sql("SELECT * FROM player_metrics ORDER BY overall_value_rank", engine)

# ── page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="NBA Player Value", layout="wide")
st.title("NBA Player Contract Value Dashboard")

# ── load data ─────────────────────────────────────────────────────────────────

df, stats_per_game, stats_per_36, stats_per_100 = load_metrics()

# df = load_metrics()

# ── player selector ───────────────────────────────────────────────────────────

player = st.selectbox(
    "Select a player",
    options=sorted(df["player"].unique())
)

player_row = df[df["player"] == player].iloc[0]
player_min = player_row["min"]

player_id = player_row["player_id"]
headshot_url = f"https://www.basketball-reference.com/req/202106291/images/headshots/{player_id}.jpg"

st.image(headshot_url)

st.divider()

# ── table 0: simple game stats ────────────────────────────────────────────────

st.subheader("Box Stats")

stat_mode = st.selectbox(
    "View stats as",
    options=["Per Game", "Per 36 Minutes", "Per 100 Possessions"],
    key="stat_mode"
)

stat_map = {
    "Per Game":             stats_per_game,
    "Per 36 Minutes":       stats_per_36,
    "Per 100 Possessions":  stats_per_100,
}

selected_stats = stat_map[stat_mode]
player_stats = selected_stats[selected_stats["player"] == player]

if not player_stats.empty:
    stats_display = pd.DataFrame({
        "MIN":  [player_stats["min"].values[0]],
        "PTS":  [player_stats["pts"].values[0]],
        "REB":  [player_stats["reb"].values[0]],
        "AST":  [player_stats["ast"].values[0]],
        "3P%":  [player_stats["fg3_pct"].values[0]],
        "2P%":  [player_stats["fg2_pct"].values[0]],
        "FT%":  [player_stats["ft_pct"].values[0]],
    }).round(3)

    if stat_mode != "Per Game":
        stats_display = stats_display.drop(columns=["MIN"])

    st.dataframe(stats_display, hide_index=True, width='content')
else:
    st.write("No stats available for this player.")
    
st.divider()

# ── table 1: advanced stats ───────────────────────────────────────────────────

st.subheader("Advanced Stats")

advanced = pd.DataFrame({
    # "MINUTES PER GAME":  [player_row["min"]],
    "PER":  [player_row["per"]],
    "BPM":  [player_row["bpm"]],
    "VORP": [player_row["vorp"]],
    "WS":   [player_row["ws"]]
}).round(2)

st.dataframe(advanced, hide_index=True, width="stretch")

# ── table 2: financial value ──────────────────────────────────────────────────

st.subheader("Contract Value")

total_global = len(df)

value = pd.DataFrame({
    "Annual Salary":    [f"${player_row['salary']:,.0f}"],
    "VORP / Dollar":    [round(player_row["vorp_per_dollar"], 10)],
    "WS / Dollar":      [round(player_row["ws_per_dollar"], 10)],
    "VORP/$ League Rank":      [f"{int(player_row['vorp_per_dollar_rank'])} of {total_global}"],
    "WS/$ League Rank":        [f"{int(player_row['ws_per_dollar_rank'])} of {total_global}"],
    "Overall Value Rank":   [f"{int(player_row['overall_value_rank'])} of {total_global}"],
})

st.dataframe(
    value,
    hide_index=True,
    width="stretch",
    column_config={
        "VORP/$ League Rank":        st.column_config.TextColumn(width="small"),
        "WS/$ League Rank":          st.column_config.TextColumn(width="small"),
        "Overall Value Rank": st.column_config.TextColumn(width="small"),
    }
)
st.caption("Overall Value Rank is computed by averaging a player's VORP/\\$ league rank and WS/\\$ league rank across all qualified players (min. 10 minutes per game), then re-ranking that average.")

# ── table 3: similar minutes comparison ──────────────────────────────────────

st.subheader("Comparison: Similar Minutes Players")

minute_delta = st.slider(
    "Minutes per game window (± from selected player)",
    min_value=1, max_value=10, value=3
)

# Filter comparison group
comp = df[
    (df["min"] >= player_min - minute_delta) &
    (df["min"] <= player_min + minute_delta) &
    (df["player"] != player)
].copy()

# Include selected player to rank within the full group
comp_with_selected = pd.concat([df[df["player"] == player], comp], ignore_index=True)

comp_with_selected["local_vorp_rank"]  = comp_with_selected["vorp_per_dollar"].rank(ascending=False).astype(int)
comp_with_selected["local_ws_rank"]    = comp_with_selected["ws_per_dollar"].rank(ascending=False).astype(int)
comp_with_selected["local_value_rank"] = (
    (comp_with_selected["local_vorp_rank"] + comp_with_selected["local_ws_rank"]) / 2
).rank(ascending=True).astype(int)

selected_local = comp_with_selected[comp_with_selected["player"] == player].iloc[0]
comp_local     = comp_with_selected[comp_with_selected["player"] != player].copy()

# Selected player row
total_in_group = len(comp_with_selected)
local_rank = int(selected_local["local_value_rank"])
global_rank = int(selected_local["overall_value_rank"])
total_global = len(df)

league_percentile = round((1 - (global_rank - 1) / total_global) * 100, 1)
group_percentile  = round((1 - (local_rank - 1) / total_in_group) * 100, 1)

selected_display = pd.DataFrame([{
    "Player":                    selected_local["player"],
    "MIN":                       selected_local["min"],
    "Salary":                    f"${selected_local['salary']:,.0f}",
    "VORP":                      round(selected_local["vorp"], 2),
    "WS":                        round(selected_local["ws"], 2),
    "BPM":                       round(selected_local["bpm"], 2),
    "PER":                       round(selected_local["per"], 2),
    "VORP/$":                    round(selected_local["vorp_per_dollar"], 10),
    "WS/$":                      round(selected_local["ws_per_dollar"], 10),
    "Group Rank":                f"{local_rank} of {total_in_group}",
    "Group Percentile":          f"Top {group_percentile}%",
    "League Percentile":         f"Top {league_percentile}%",
}])

st.dataframe(
    selected_display,
    hide_index=True,
    width="stretch",
    column_config={
        "Local Value Rank": st.column_config.TextColumn(width="small"),
        "Group Percentile": st.column_config.TextColumn(width="small"),
        "League Percentile": st.column_config.TextColumn(width="small"),
    }
)

# Comparison table

comp_display = comp_with_selected[[
    "player", "min", "salary", "vorp", "ws", "bpm", "per",
    "vorp_per_dollar", "ws_per_dollar", "local_value_rank"
]].rename(columns={
    "player":           "Player",
    "min":              "MIN",
    "salary":           "Salary",
    "vorp":             "VORP",
    "ws":               "WS",
    "bpm":              "BPM",
    "per":              "PER",
    "vorp_per_dollar":  "VORP/$",
    "ws_per_dollar":    "WS/$",
    "local_value_rank": "Local Value Rank",
}).sort_values("Local Value Rank")

# Round only the desired columns
cols_to_round = ["MIN", "Salary", "VORP", "WS", "BPM", "PER"]
comp_display[cols_to_round] = comp_display[cols_to_round].round(2)

comp_display["Salary"] = comp_display["Salary"].apply(lambda x: f"${x:,.0f}")

# Highlight the selected player
##ed4585, #2e4057
def highlight_selected(row, player_name):
    if row["Player"] == player_name:
        return ["background-color: #ed4585; color: white"] * len(row)
    return [""] * len(row)

styled_comp_display = comp_display.style.apply(
    highlight_selected,
    player_name=player,
    axis=1
)

st.dataframe(styled_comp_display, hide_index=True, width="stretch")

st.caption("All statistics are for the current NBA season. Data updated daily at 1am PST")