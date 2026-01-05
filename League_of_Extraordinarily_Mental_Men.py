import streamlit as st
import requests
import pandas as pd

# --- SETTINGS ---
LEAGUE_ID = "1239058549716303872"
st.set_page_config(page_title="League of Extraordinarily Mental Men", page_icon="🏈", layout="wide")

def get_letter_grade(points, pos):
    ceilings = {'QB': 24, 'RB': 18, 'WR': 18, 'TE': 14, 'K': 10, 'DEF': 10}
    ceiling = ceilings.get(pos, 15)
    pct = (points / ceiling) * 100
    if pct >= 90: return "A+"
    elif pct >= 80: return "A"
    elif pct >= 70: return "B"
    elif pct >= 60: return "C"
    elif pct >= 50: return "D"
    return "F"

@st.cache_data(ttl=60)
def fetch_league_data(selected_week):
    players = requests.get("https://api.sleeper.app/v1/players/nfl").json()
    rosters = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/rosters").json()
    users = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/users").json()
    proj = requests.get(f"https://api.sleeper.app/v1/stats/nfl/regular/2025/{selected_week}").json()
    actual = requests.get(f"https://api.sleeper.app/v1/stats/nfl/regular/2025/{selected_week}").json()
    
    user_map = {u['user_id']: {"name": u.get('metadata', {}).get('team_name') or u.get('display_name'), "avatar": u.get('avatar')} for u in users}
    roster_to_name = {r['roster_id']: user_map.get(r['owner_id'], {}).get('name', 'Unknown') for r in rosters}
    rostered_ids = {p for r in rosters if r['players'] for p in r['players']}
    
    return players, rosters, proj, actual, user_map, rostered_ids, roster_to_name

# --- SIDEBAR ---
state = requests.get("https://api.sleeper.app/v1/state/nfl").json()
view_week = st.sidebar.slider("NFL Week", 1, 18, value=state['week'])
players, rosters, projections, actual_stats, user_map, rostered_ids, roster_to_name = fetch_league_data(view_week)

selection = st.sidebar.selectbox("Navigation", ["🔥 BOOM & CHOKE", "FREE AGENTS"] + sorted([u['name'] for u in user_map.values()]))

# --- MAIN CONTENT ---
st.title("🏈 Mental Men: Premier Analytics")

if selection == "🔥 BOOM & CHOKE":
    st.header(f"Live Performance Tracker - Week {view_week}")
    boom_list = []
    for r in rosters:
        owner = roster_to_name[r['roster_id']]
        for pid in (r['players'] or []):
            p = players.get(pid, {})
            p_name = p.get('full_name') or f"{p.get('team', 'UNK')} DEF"
            act = actual_stats.get(pid, {}).get('pts_ppr', 0)
            proj = projections.get(pid, {}).get('pts_ppr', 0)
            diff = act - proj
            if proj > 4:
                status = "🔥 BOOMING" if diff > 7 else "❄️ CHOKING" if diff < -7 else "⚪ NORMAL"
                boom_list.append({"Player": p_name, "Team": owner, "Score": act, "Proj": proj, "Gap": round(diff, 1), "Status": status})
    
    df_boom = pd.DataFrame(boom_list).sort_values(by="Gap", ascending=False)
    st.table(df_boom)

elif selection == "FREE AGENTS":
    st.header("Best Available Players")
    tabs = st.tabs(["QB", "RB", "WR", "TE", "K", "DEF"])
    fa_list = [{"Pos": p.get('position'), "Player": p.get('full_name') or f"{p.get('team')} DEF", "Points": actual_stats.get(pid, {}).get('pts_ppr', 0)} 
               for pid, p in players.items() if pid not in rostered_ids and p.get('position') in ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']]
    df_fa = pd.DataFrame(fa_list)
    for i, pos in enumerate(["QB", "RB", "WR", "TE", "K", "DEF"]):
        with tabs[i]:
            st.table(df_fa[df_fa['Pos'] == pos].sort_values(by="Points", ascending=False).head(10))

else:
    # TEAM REPORT CARD
    st.header(f"Report Card: {selection}")
    selected_roster = next((r for r in rosters if user_map.get(r['owner_id'], {}).get('name') == selection), None)
    if selected_roster:
        team_data = []
        for pid in (selected_roster['players'] or []):
            p = players.get(pid, {})
            score = actual_stats.get(pid, {}).get('pts_ppr', 0)
            team_data.append({"Pos": p.get('position', '??'), "Player": p.get('full_name') or f"{p.get('team', 'UNK')} DEF", "Points": score, "Grade": get_letter_grade(score, p.get('position', '??'))})
        
        df_team = pd.DataFrame(team_data).sort_values(by="Points", ascending=False)
        avg_score = df_team['Points'].mean() if not df_team.empty else 0
        gpa = round((avg_score / 14) * 4.0, 2)
        st.metric("Weekly GPA", f"{min(gpa, 4.0)} / 4.0")
        st.table(df_team)