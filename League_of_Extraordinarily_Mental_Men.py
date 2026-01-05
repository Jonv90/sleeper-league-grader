import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# CONFIG
LEAGUE_ID = "1239058549716303872"
st.set_page_config(page_title="Premier League Analytics", page_icon="📈", layout="wide")

# --- SMART GRADING LOGIC ---
def get_letter_grade(points, pos):
    ceilings = {'QB': 24, 'RB': 18, 'WR': 18, 'TE': 14, 'K': 10, 'DEF': 10}
    ceiling = ceilings.get(pos, 15)
    pct = (points / ceiling) * 100
    if pct >= 90: return "A+"
    if pct >= 80: return "A"
    if pct >= 70: return "B"
    if pct >= 60: return "C"
    if pct >= 50: return "D"
    return "F"

@st.cache_data(ttl=60) # Live-updates every 60 seconds
def fetch_premier_data(selected_week):
    # Core Data
    players = requests.get("https://api.sleeper.app/v1/players/nfl").json()
    rosters = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/rosters").json()
    users = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/users").json()
    matchups = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/matchups/{selected_week}").json()
    
    # Projections vs Actuals
    proj = requests.get(f"https://api.sleeper.app/v1/stats/nfl/regular/2025/{selected_week}").json()
    actual = requests.get(f"https://api.sleeper.app/v1/stats/nfl/regular/2025/{selected_week}").json()
    
    user_data_map = {u['user_id']: {"name": u.get('metadata', {}).get('team_name') or u.get('display_name'), "avatar": u.get('avatar')} for u in users}
    roster_to_user = {r['roster_id']: user_data_map.get(r['owner_id'], {}).get('name', 'Unknown') for r in rosters}
    rostered_ids = {p for r in rosters if r['players'] for p in r['players']}
        
    return players, rosters, proj, actual, user_data_map, rostered_ids, roster_to_user, matchups

# --- SIDEBAR & STATE ---
initial_state = requests.get("https://api.sleeper.app/v1/state/nfl").json()
view_week = st.sidebar.slider("NFL Week", 1, 18, value=initial_state['week'])
players, rosters, projections, actual_stats, user_data_map, rostered_ids, roster_to_user, matchups = fetch_premier_data(view_week)

# --- UI MAIN ---
st.title("📈 Mental Men: Premier League Analytics")
st.caption(f"LIVE DATA FOR WEEK {view_week} • NFL SEASON: {initial_state['season_type'].upper()}")

team_names_list = sorted([u['name'] for u in user_data_map.values()])
selection = st.sidebar.selectbox("Select View", ["🏟️ LIVE MATCHUPS", "🔥 BOOM/CHOKE TRACKER", "FREE AGENTS"] + team_names_list)

# --- CONTENT SECTIONS ---

if selection == "🏟️ LIVE MATCHUPS":
    st.header("Live Win Probability")
    matchup_groups = {}
    for m in matchups:
        mid = m['matchup_id']
        if mid not in matchup_groups: matchup_groups[mid] = []
        matchup_groups[mid].append(m)
    
    for mid, teams in matchup_groups.items():
        if len(teams) < 2: continue
        t1, t2 = teams[0], teams[1]
        t1_name, t2_name = roster_to_user[t1['roster_id']], roster_to_user[t2['roster_id']]
        
        # Win Prob = (Actual Score) / (Total Combined Score)
        t1_score = t1['points']
        t2_score = t2['points']
        
        col1, col2 = st.columns([1, 1])
        with col1: st.subheader(f"{t1_name} ({t1_score:.1f})")
        with col2: st.subheader(f"({t2_score:.1f}) {t2_name}")
        st.progress(t1_score / (t1_score + t2_score + 0.1))
        st.divider()

elif selection == "🔥 BOOM/CHOKE TRACKER":
    st.header("🚨 Choke & Boom Alert")
    boom_list = []
    for r in rosters:
        owner = roster_to_user[r['roster_id']]
        for pid in (r['players'] or []):
            p = players.get(pid, {})
            p_name = p.get('full_name') or f"{p.get('team', 'UNK')} DEF"
            act = actual_stats.get(pid, {}).get('pts_ppr', 0)
            proj = projections.get(pid, {}).get('pts_ppr', 0)
            diff = act - proj
            
            if proj > 4.0: # Filter out irrelevant depth
                alert = "🔥 BOOMING" if diff > 8 else "❄️ CHOKING" if diff < -8 else "⚪ NEUTRAL"
                boom_list.append({"Player": p_name, "Team": owner, "Score": act, "Proj": proj, "Gap": round(diff, 1), "Status": alert})
    
    df_boom = pd.DataFrame(boom_list).sort_values(by="Gap", ascending=False)
    st.dataframe(df_boom.style.applymap(lambda x: 'color: red' if x == "❄️ CHOKING" else ('color: green' if x == "🔥 BOOMING" else ''), subset=['Status']), use_container_width=True)

elif selection == "FREE AGENTS":
    st.subheader(f"Best Available (Week {view_week})")
    tabs = st.tabs(["QB", "RB", "WR", "TE", "K", "DEF"])
    fa_list = [{"Pos": p.get('position'), "Player": p.get('full_name') or f"{p.get('team')} DEF", "Proj": projections.get(pid, {}).get('pts_ppr', 0), "Grade": get_letter_grade(projections.get(pid, {}).get('pts_ppr', 0), p.get('position'))} 
               for pid, p in players.items() if pid not in rostered_ids and p.get('position') in ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']]
    df_fa = pd.DataFrame(fa_list)
    for i, pos in enumerate(["QB", "RB", "WR", "TE", "K", "DEF"]):
        with tabs[i]: st.table(df_fa[(df_fa['Pos'] == pos) & (df_fa['Proj'] > 1)].sort_values(by="Proj", ascending=False).head(10))

else:
    # TEAM REPORT CARD
    st.subheader(f"Report Card: {selection}")
    selected_roster = next((r for r in rosters if user_data_map.get(r['owner_id'], {}).get('name') == selection), None)
    if selected_roster:
        team_data = []
        for pid in (selected_roster['players'] or []):
            p = players.get(pid, {})
            p_name = p.get('full_name') or f"{p.get('team', 'UNK')} DEF"
            score = actual_stats.get(pid, {}).get('pts_ppr', 0)
            team_data.append({"Pos": p.get('position', '??'), "Player": p_name, "Points": score, "Grade": get_letter_grade(score, p.get('position', '??'))})
        
        avg_pts = sum(p['Points'] for p in team_data) / len(team_data) if team_data else 0
        gpa = round((avg_pts / 12) * 4.0, 2)
        st.metric(label="Calculated GPA", value=f"{min(gpa, 4.0)} / 4.0")
        st.table(pd.DataFrame(team_data).sort_values(by="Points", ascending=False))