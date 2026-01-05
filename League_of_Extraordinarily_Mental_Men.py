import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# CONFIG
LEAGUE_ID = "1239058549716303872"
st.set_page_config(page_title="League of Extraordinarily Mental Men", page_icon="🏈", layout="wide")

@st.cache_data
def fetch_all_data():
    state = requests.get("https://api.sleeper.app/v1/state/nfl").json()
    week = state['week']
    players = requests.get("https://api.sleeper.app/v1/players/nfl").json()
    rosters = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/rosters").json()
    projections = requests.get(f"https://api.sleeper.app/v1/stats/nfl/regular/2025/{week}").json()
    users = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/users").json()
    
    user_map = {u['user_id']: (u.get('metadata', {}).get('team_name') or u.get('display_name')) for u in users}
    
    rostered_ids = set()
    for r in rosters:
        rostered_ids.update(r['players'] or [])
        
    return players, rosters, projections, week, user_map, rostered_ids

# UI ELEMENTS
st.title("🏈 League of Extraordinarily Mental Men")
players, rosters, projections, week, user_map, rostered_ids = fetch_all_data()

# TIMESTAMP
now = datetime.now().strftime("%B %d, %I:%M %p")
st.caption(f"Last Updated: {now} (Projections Refresh on Page Load)")

# --- SIDEBAR UPDATED ---
team_names = [user_map.get(r['owner_id'], f"Team {r['roster_id']}") for r in rosters]
# Added "🔥 HOT OR NOT" to the list
selection = st.sidebar.selectbox("Select View", ["FREE AGENTS", "🔥 HOT OR NOT"] + team_names)

# NEW: REFRESH BUTTON AT BOTTOM OF SIDEBAR
with st.sidebar:
    st.divider()
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# DATA PROCESSING
table_data = []

# --- NEW SECTION: HOT OR NOT ---
if selection == "🔥 HOT OR NOT":
    st.header("🔥 Hot or Not ❄️")
    st.info(f"Top and Bottom Projections for NFL Week {week}")

    # Create a list of all rostered players with their projections
    all_rostered_stats = []
    for r in rosters:
        owner_name = user_map.get(r['owner_id'], f"Team {r['roster_id']}")
        for p_id in r['players']:
            p_info = players.get(p_id, {})
            proj = projections.get(p_id, {}).get('pts_ppr', 0)
            if proj > 0:
                all_rostered_stats.append({
                    "Player": p_info.get('full_name'),
                    "Team": owner_name,
                    "Pos": p_info.get('position'),
                    "Proj": proj
                })

    # Convert to Dataframe for easy sorting
    df_trends = pd.DataFrame(all_rostered_stats)

    if not df_trends.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔥 Trending Up")
            st.write("Highest Projected Players this Week")
            top_5 = df_trends.sort_values(by="Proj", ascending=False).head(5)
            for _, row in top_5.iterrows():
                st.success(f"**{row['Player']}** ({row['Pos']})\n\n{row['Proj']} pts — Owner: {row['Team']}")

        with col2:
            st.subheader("❄️ Trending Down")
            st.write("Lowest Projected Starters (Risk)")
            # Filtering for common starters (usually players projected over 5 pts but on the low end)
            bottom_5 = df_trends[df_trends['Proj'] > 5].sort_values(by="Proj", ascending=True).head(5)
            for _, row in bottom_5.iterrows():
                st.error(f"**{row['Player']}** ({row['Pos']})\n\n{row['Proj']} pts — Owner: {row['Team']}")
    else:
        st.write("No rostered player data found to analyze.")

elif selection == "FREE AGENTS":
    st.subheader("🔥 Best Available Free Agents")
    
    # 1. Expand the tabs to include DEF and K
    tab_qb, tab_rb, tab_wr, tab_te, tab_k, tab_def = st.tabs(["QB", "RB", "WR", "TE", "K", "DEF"])
    
    # 2. Gather FA data
    fa_list = []
    for p_id, p_info in players.items():
        if p_id not in rostered_ids:
            pos = p_info.get('position')
            if pos in ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']:
                proj = projections.get(p_id, {}).get('pts_ppr', 0)
                if proj > 0.5:
                    fa_list.append({
                        "Position": pos,
                        "Player": p_info.get('full_name') or f"{p_info.get('team')} DEF",
                        "Projection": proj,
                        "Grade": min(round((proj / 25) * 100), 100)
                    })
    
    df_fa = pd.DataFrame(fa_list)

    def display_pos_table(df, pos):
        pos_df = df[df['Position'] == pos].sort_values(by="Grade", ascending=False).head(15)
        if not pos_df.empty:
            st.table(pos_df)
        else:
            st.write(f"No {pos}s available.")

    with tab_qb: display_pos_table(df_fa, "QB")
    with tab_rb: display_pos_table(df_fa, "RB")
    with tab_wr: display_pos_table(df_fa, "WR")
    with tab_te: display_pos_table(df_fa, "TE")
    with tab_k:  display_pos_table(df_fa, "K")
    with tab_def: display_pos_table(df_fa, "DEF")

else:
    # Logic for viewing a specific team
    st.subheader(f"Analysis for: {selection}")
    selected_roster = next(r for r in rosters if user_map.get(r['owner_id']) == selection or f"Team {r['roster_id']}" == selection)
    for p_id in selected_roster['players']:
        p_info = players.get(p_id, {})
        proj = projections.get(p_id, {}).get('pts_ppr', 0)
        table_data.append({
            "Position": p_info.get('position', '??'),
            "Player": p_info.get('full_name') or f"{p_info.get('team')} DEF",
            "Projection": proj,
            "Grade": min(round((proj / 25) * 100), 100)
        })

    # Only display this table if we are in a team view
    df = pd.DataFrame(table_data)
    if not df.empty:
        st.table(df.sort_values(by="Grade", ascending=False))