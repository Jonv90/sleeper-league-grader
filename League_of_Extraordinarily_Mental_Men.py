import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# CONFIG
LEAGUE_ID = "1239058549716303872"
st.set_page_config(page_title="League of Extraordinarily Mental Men", page_icon="🏈", layout="wide")

# --- SMART GRADING LOGIC ---
def get_letter_grade(points, pos):
    ceilings = {'QB': 24, 'RB': 18, 'WR': 18, 'TE': 14, 'K': 9, 'DEF': 9}
    ceiling = ceilings.get(pos, 15)
    pct = (points / ceiling) * 100
    if pct >= 90: return "A+"
    if pct >= 80: return "A"
    if pct >= 70: return "B"
    if pct >= 60: return "C"
    if pct >= 50: return "D"
    return "F"

@st.cache_data
def fetch_all_data(selected_week):
    # We fetch the stats specifically for the selected_week
    state = requests.get("https://api.sleeper.app/v1/state/nfl").json()
    current_real_week = state['week']
    players = requests.get("https://api.sleeper.app/v1/players/nfl").json()
    rosters = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/rosters").json()
    users = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/users").json()
    
    # Projections for the specific week selected by the user
    projections = requests.get(f"https://api.sleeper.app/v1/stats/nfl/regular/2025/{selected_week}").json()
    
    user_data_map = {u['user_id']: {"name": u.get('metadata', {}).get('team_name') or u.get('display_name'), "avatar": u.get('avatar')} for u in users}
    rostered_ids = {p for r in rosters if r['players'] for p in r['players']}
        
    return players, rosters, projections, current_real_week, user_data_map, rostered_ids

# --- SIDEBAR CONTROLS ---
# Get current week first to set the slider default
initial_state = requests.get("https://api.sleeper.app/v1/state/nfl").json()
current_week = initial_state['week']

st.sidebar.title("Settings")
view_week = st.sidebar.slider("Select NFL Week", 1, 18, value=current_week)

# Fetch data based on the slider
players, rosters, projections, _, user_data_map, rostered_ids = fetch_all_data(view_week)

# --- UI MAIN ---
st.title("🏈 League of Extraordinarily Mental Men")
st.subheader(f"Data for NFL Week {view_week}")

team_names_list = [user_data_map.get(r['owner_id'], {}).get('name', f"Team {r['roster_id']}") for r in rosters]
selection = st.sidebar.selectbox("Select View", ["FREE AGENTS", "🔥 HOT OR NOT"] + sorted(team_names_list))

# --- CONTENT SECTIONS ---
if selection == "🔥 HOT OR NOT":
    st.header(f"🔥 Hot or Not ❄️ (Week {view_week})")
    all_stats = []
    for r in rosters:
        owner_name = user_data_map.get(r['owner_id'], {}).get('name', "Unknown")
        for p_id in (r['players'] or []):
            p_info = players.get(p_id, {})
            p_name = p_info.get('full_name') or f"{p_info.get('team', 'UNK')} DEF"
            pos = p_info.get('position', '??')
            proj = projections.get(p_id, {}).get('pts_ppr', 0)
            if proj > 0:
                all_stats.append({"Player": p_name, "Team": owner_name, "Pos": pos, "Proj": proj, "Grade": get_letter_grade(proj, pos)})
    
    df_trends = pd.DataFrame(all_stats)
    if not df_trends.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔥 Top Performers")
            for _, row in df_trends.sort_values(by="Proj", ascending=False).head(5).iterrows():
                st.success(f"**{row['Player']}** ({row['Pos']}) — **{row['Grade']}**\n\n{row['Proj']} pts — {row['Team']}")
        with col2:
            st.subheader("❄️ Underperformers")
            for _, row in df_trends[df_trends['Proj'] > 3].sort_values(by="Proj", ascending=True).head(5).iterrows():
                st.error(f"**{row['Player']}** ({row['Pos']}) — **{row['Grade']}**\n\n{row['Proj']} pts — {row['Team']}")

elif selection == "FREE AGENTS":
    st.subheader(f"🔥 Best Available (Week {view_week})")
    tabs = st.tabs(["QB", "RB", "WR", "TE", "K", "DEF"])
    fa_list = [{"Position": p_info.get('position'), "Player": p_info.get('full_name') or f"{p_info.get('team')} DEF", "Proj": projections.get(p_id, {}).get('pts_ppr', 0), "Grade": get_letter_grade(projections.get(p_id, {}).get('pts_ppr', 0), p_info.get('position'))} 
               for p_id, p_info in players.items() if p_id not in rostered_ids and p_info.get('position') in ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']]
    df_fa = pd.DataFrame(fa_list)
    for i, pos in enumerate(["QB", "RB", "WR", "TE", "K", "DEF"]):
        with tabs[i]:
            st.table(df_fa[(df_fa['Position'] == pos) & (df_fa['Proj'] > 1)].sort_values(by="Proj", ascending=False).head(15))

else:
    # TEAM REPORT CARD
    st.subheader(f"Week {view_week} Report Card: {selection}")
    selected_roster = next((r for r in rosters if user_data_map.get(r['owner_id'], {}).get('name') == selection), None)
    if selected_roster:
        col_avatar, col_gpa = st.columns([1, 3])
        team_data = [{"Pos": (p := players.get(pid, {})).get('position', '??'), "Player": p.get('full_name') or f"{p.get('team', 'UNK')} DEF", "Proj": (pr := projections.get(pid, {}).get('pts_ppr', 0)), "Grade": get_letter_grade(pr, p.get('position', '??'))} for pid in (selected_roster['players'] or [])]
        
        gpa = round((sum(p['Proj'] for p in team_data) / len(team_data) / 15) * 4.0, 2) if team_data else 0
        with col_avatar:
            if (av := user_data_map.get(selected_roster['owner_id'], {}).get('avatar')): st.image(f"https://sleepercdn.com/avatars/thumbs/{av}", width=100)
        with col_gpa: st.metric(label="Weekly Team GPA", value=f"{gpa} / 4.0")
        st.table(pd.DataFrame(team_data).sort_values(by="Proj", ascending=False))