import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# CONFIG
LEAGUE_ID = "1239058549716303872"
st.set_page_config(page_title="League of Extraordinarily Mental Men", page_icon="🏈", layout="wide")

# --- UPDATED GRADING LOGIC ---
def get_letter_grade(points, pos):
    """Grades players on a curve based on their position."""
    # Set the '100%' mark differently for each position
    ceilings = {
        'QB': 25,
        'RB': 20,
        'WR': 20,
        'TE': 18,
        'K': 10,
        'DEF': 10
    }
    
    # Get the ceiling for the position, default to 20 if unknown
    ceiling = ceilings.get(pos, 20)
    pct = (points / ceiling) * 100
    
    if pct >= 90: return "A+"
    if pct >= 80: return "A"
    if pct >= 70: return "B"
    if pct >= 60: return "C"
    if pct >= 50: return "D"
    return "F"

# --- INITIALIZE TIMESTAMP ---
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
    
    user_data_map = {}
    for u in users:
        uid = u['user_id']
        display_name = u.get('display_name', f"User {uid}")
        team_name = u.get('metadata', {}).get('team_name') or display_name
        avatar = u.get('avatar')
        user_data_map[uid] = {"name": team_name, "avatar": avatar}
    
    rostered_ids = set()
    for r in rosters:
        if r['players']:
            rostered_ids.update(r['players'])
        
    return players, rosters, projections, week, user_data_map, rostered_ids

players, rosters, projections, week, user_data_map, rostered_ids = fetch_all_data()

# UI
st.title("🏈 League of Extraordinarily Mental Men")
st.caption(f"Last Updated: {st.session_state.last_update}")

# --- SIDEBAR ---
team_names_list = []
for r in rosters:
    name = user_data_map.get(r['owner_id'], {}).get('name', f"Team {r['roster_id']}")
    team_names_list.append(name)

selection = st.sidebar.selectbox("Select View", ["FREE AGENTS", "🔥 HOT OR NOT"] + sorted(team_names_list))

with st.sidebar:
    st.divider()
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.session_state.last_update = datetime.now().strftime("%B %d, %I:%M %p")
        st.rerun()

# --- CONTENT ---

if selection == "🔥 HOT OR NOT":
    st.header("🔥 Hot or Not ❄️")
    all_rostered_stats = []
    for r in rosters:
        owner_name = user_data_map.get(r['owner_id'], {}).get('name', "Unknown")
        for p_id in (r['players'] or []):
            p_info = players.get(p_id, {})
            # FIX: Check for Defense name
            p_name = p_info.get('full_name') or f"{p_info.get('team', 'UNK')} DEF"
            proj = projections.get(p_id, {}).get('pts_ppr', 0)
            if proj > 0:
                all_rostered_stats.append({
                    "Player": p_name,
                    "Team": owner_name,
                    "Pos": p_info.get('position', '??'),
                    "Proj": proj,
                    "Grade": get_letter_grade(proj)
                })
    df_trends = pd.DataFrame(all_rostered_stats)
    if not df_trends.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔥 Trending Up")
            top_5 = df_trends.sort_values(by="Proj", ascending=False).head(5)
            for _, row in top_5.iterrows():
                st.success(f"**{row['Player']}** — Grade: **{row['Grade']}**\n\n{row['Proj']} pts ({row['Team']})")
        with col2:
            st.subheader("❄️ Trending Down")
            bottom_5 = df_trends[df_trends['Proj'] > 5].sort_values(by="Proj", ascending=True).head(5)
            for _, row in bottom_5.iterrows():
                st.error(f"**{row['Player']}** — Grade: **{row['Grade']}**\n\n{row['Proj']} pts ({row['Team']})")

elif selection == "FREE AGENTS":
    st.subheader("🔥 Best Available Free Agents")
    tabs = st.tabs(["QB", "RB", "WR", "TE", "K", "DEF"])
    fa_list = []
    for p_id, p_info in players.items():
        if p_id not in rostered_ids:
            pos = p_info.get('position')
            if pos in ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']:
                proj = projections.get(p_id, {}).get('pts_ppr', 0)
                if proj > 1.0:
                    p_name = p_info.get('full_name') or f"{p_info.get('team', 'UNK')} DEF"
                    fa_list.append({"Position": pos, "Player": p_name, "Proj": proj, "Grade": get_letter_grade(proj)})
    df_fa = pd.DataFrame(fa_list)
    for i, pos in enumerate(["QB", "RB", "WR", "TE", "K", "DEF"]):
        with tabs[i]:
            pos_df = df_fa[df_fa['Position'] == pos].sort_values(by="Proj", ascending=False).head(15)
            st.table(pos_df)

else:
    # TEAM VIEW / REPORT CARD
    st.subheader(f"Report Card: {selection}")
    selected_roster = next((r for r in rosters if user_data_map.get(r['owner_id'], {}).get('name') == selection), None)
    
    if selected_roster:
        col_avatar, col_gpa = st.columns([1, 3])
        
        team_data = []
        for p_id in (selected_roster['players'] or []):
            p_info = players.get(p_id, {})
            p_name = p_info.get('full_name') or f"{p_info.get('team', 'UNK')} DEF"
            proj = projections.get(p_id, {}).get('pts_ppr', 0)
            team_data.append({
                "Pos": p_info.get('position', '??'),
                "Player": p_name,
                "Proj": proj,
                "Grade": get_letter_grade(proj)
            })
        
        # Calculate GPA
        avg_proj = sum(p['Proj'] for p in team_data) / len(team_data) if team_data else 0
        gpa = round((avg_proj / 25) * 4.0, 2)

        with col_avatar:
            avatar_id = user_data_map.get(selected_roster['owner_id'], {}).get('avatar')
            if avatar_id:
                st.image(f"https://sleepercdn.com/avatars/thumbs/{avatar_id}", width=100)
        with col_gpa:
            st.metric(label="Weekly Team GPA", value=f"{gpa} / 4.0")

        st.table(pd.DataFrame(team_data).sort_values(by="Proj", ascending=False))