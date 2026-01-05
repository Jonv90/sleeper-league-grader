import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# CONFIG
LEAGUE_ID = "1239058549716303872"
st.set_page_config(page_title="League of Extraordinarily Mental Men", page_icon="🏈", layout="wide")

# --- INITIALIZE TIMESTAMP IN MEMORY ---
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now().strftime("%B %d, %I:%M %p")

@st.cache_data
def fetch_all_data():
    state = requests.get("https://api.sleeper.app/v1/state/nfl").json()
    week = state['week']
    players = requests.get("https://api.sleeper.app/v1/players/nfl").json()
    rosters = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/rosters").json()
    projections = requests.get(f"https://api.sleeper.app/v1/stats/nfl/regular/2025/{week}").json()
    users = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/users").json()
    
    # Map user IDs to team names and avatars
    user_data_map = {}
    for u in users:
        display_name = u.get('metadata', {}).get('team_name') or u.get('display_name')
        avatar = u.get('avatar')
        user_data_map[u['user_id']] = {"name": display_name, "avatar": avatar}
    
    rostered_ids = set()
    for r in rosters:
        rostered_ids.update(r['players'] or [])
        
    return players, rosters, projections, week, user_data_map, rostered_ids

# UI ELEMENTS
st.title("🏈 League of Extraordinarily Mental Men")
players, rosters, projections, week, user_data_map, rostered_ids = fetch_all_data()

# DISPLAY THE TIMESTAMP
st.caption(f"Last Updated: {st.session_state.last_update} (Projections Refresh on Page Load)")

# --- SIDEBAR ---
team_names = [user_data_map.get(r['owner_id'], {}).get('name', f"Team {r['roster_id']}") for r in rosters]
selection = st.sidebar.selectbox("Select View", ["FREE AGENTS", "🔥 HOT OR NOT"] + team_names)

with st.sidebar:
    st.divider()
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        # Update the timestamp exactly when button is clicked
        st.session_state.last_update = datetime.now().strftime("%B %d, %I:%M %p")
        st.rerun()

# --- LOGIC SECTIONS ---

if selection == "🔥 HOT OR NOT":
    st.header("🔥 Hot or Not ❄️")
    st.info(f"Top and Bottom Projections for NFL Week {week}")

    all_rostered_stats = []
    for r in rosters:
        owner_name = user_data_map.get(r['owner_id'], {}).get('name', "Unknown")
        for p_id in (r['players'] or []):
            p_info = players.get(p_id, {})
            proj = projections.get(p_id, {}).get('pts_ppr', 0)
            if proj > 0:
                all_rostered_stats.append({
                    "Player": p_info.get('full_name') or f"{p_info.get('team')} DEF",
                    "Team": owner_name,
                    "Pos": p_info.get('position'),
                    "Proj": proj
                })

    df_trends = pd.DataFrame(all_rostered_stats)
    if not df_trends.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔥 Trending Up")
            top_5 = df_trends.sort_values(by="Proj", ascending=False).head(5)
            for _, row in top_5.iterrows():
                st.success(f"**{row['Player']}** ({row['Pos']})\n\n{row['Proj']} pts — Owner: {row['Team']}")
        with col2:
            st.subheader("❄️ Trending Down")
            bottom_5 = df_trends[df_trends['Proj'] > 5].sort_values(by="Proj", ascending=True).head(5)
            for _, row in bottom_5.iterrows():
                st.error(f"**{row['Player']}** ({row['Pos']})\n\n{row['Proj']} pts — Owner: {row['Team']}")

elif selection == "FREE AGENTS":
    st.subheader("🔥 Best Available Free Agents")
    tab_qb, tab_rb, tab_wr, tab_te, tab_k, tab_def = st.tabs(["QB", "RB", "WR", "TE", "K", "DEF"])
    
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
        st.table(pos_df) if not pos_df.empty else st.write(f"No {pos}s available.")

    with tab_qb: display_pos_table(df_fa, "QB")
    with tab_rb: display_pos_table(df_fa, "RB")
    with tab_wr: display_pos_table(df_fa, "WR")
    with tab_te: display_pos_table(df_fa, "TE")
    with tab_k:  display_pos_table(df_fa, "K")
    with tab_def: display_pos_table(df_fa, "DEF")

else:
    # Logic for viewing a specific team
    st.subheader(f"Analysis for: {selection}")
    selected_roster = next(r for r in rosters if user_data_map.get(r['owner_id'], {}).get('name') == selection or f"Team {r['roster_id']}" == selection)
    
    # Show Avatar if available
    avatar_id = user_data_map.get(selected_roster['owner_id'], {}).get('avatar')
    if avatar_id:
        st.image(f"https://sleepercdn.com/avatars/thumbs/{avatar_id}", width=100)
    
    table_data = []
    for p_id in (selected_roster['players'] or []):
        p_info = players.get(p_id, {})
        proj = projections.get(p_id, {}).get('pts_ppr', 0)
        table_data.append({
            "Position": p_info.get('position', '??'),
            "Player": p_info.get('full_name') or f"{p_info.get('team')} DEF",
            "Projection": proj,
            "Grade": min(round((proj / 25) * 100), 100)
        })
    df = pd.DataFrame(table_data)
    if not df.empty:
        st.table(df.sort_values(by="Grade", ascending=False))