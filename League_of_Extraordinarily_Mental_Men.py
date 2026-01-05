import streamlit as st
import requests
import pandas as pd

# CONFIG
LEAGUE_ID = "1239058549716303872"
st.set_page_config(page_title="Fantasy Grader", page_icon="🏈", layout="wide")

@st.cache_data
def fetch_all_data():
    state = requests.get("https://api.sleeper.app/v1/state/nfl").json()
    week = state['week']
    players = requests.get("https://api.sleeper.app/v1/players/nfl").json()
    rosters = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/rosters").json()
    projections = requests.get(f"https://api.sleeper.app/v1/stats/nfl/regular/2025/{week}").json()
    users = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/users").json()
    
    user_map = {u['user_id']: (u.get('metadata', {}).get('team_name') or u.get('display_name')) for u in users}
    
    # NEW: Create a set of all rostered player IDs
    rostered_ids = set()
    for r in rosters:
        rostered_ids.update(r['players'] or [])
        
    return players, rosters, projections, week, user_map, rostered_ids

# UI ELEMENTS
st.title("🏈 Fantasy Football Grader")
players, rosters, projections, week, user_map, rostered_ids = fetch_all_data()

# SIDEBAR: Add "FREE AGENTS" to the list
team_names = [user_map.get(r['owner_id'], f"Team {r['roster_id']}") for r in rosters]
selection = st.sidebar.selectbox("Select View", ["FREE AGENTS"] + team_names)

# DATA PROCESSING
table_data = []

if selection == "FREE AGENTS":
    st.subheader("🔥 Best Available Free Agents")
    
    # 1. Expand the tabs to include DEF and K
    tab_qb, tab_rb, tab_wr, tab_te, tab_k, tab_def = st.tabs(["QB", "RB", "WR", "TE", "K", "DEF"])
    
    # 2. Gather FA data (including K and DEF)
    fa_list = []
    for p_id, p_info in players.items():
        if p_id not in rostered_ids:
            pos = p_info.get('position')
            # Check for all target positions
            if pos in ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']:
                proj = projections.get(p_id, {}).get('pts_ppr', 0)
                if proj > 0.5: # Lowered threshold slightly for kickers/defense
                    fa_list.append({
                        "Position": pos,
                        "Player": p_info.get('full_name') or f"{p_info.get('team')} DEF",
                        "Projection": proj,
                        "Grade": min(round((proj / 25) * 100), 100)
                    })
    
    df_fa = pd.DataFrame(fa_list)

    # 3. Helper to display (using the function from before)
    def display_pos_table(df, pos):
        pos_df = df[df['Position'] == pos].sort_values(by="Grade", ascending=False).head(15)
        if not pos_df.empty:
            st.table(pos_df)
        else:
            st.write(f"No {pos}s available.")

    # 4. Map data to the new tabs
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

# DISPLAY TABLE
df = pd.DataFrame(table_data)
if not df.empty:
    st.table(df.sort_values(by="Grade", ascending=False).head(45) if selection == "FREE AGENTS" else df.sort_values(by="Grade", ascending=False))
else:
    st.write("No players found.")
