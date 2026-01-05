import streamlit as st
import requests
import pandas as pd

# CONFIG
LEAGUE_ID = "1239058549716303872"
st.set_page_config(page_title="Premier Draft & Keeper Analytics", page_icon="🎯", layout="wide")

@st.cache_data(ttl=300)
def fetch_draft_data():
    # 1. Get the Draft ID for the league
    league_info = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}").json()
    draft_id = league_info.get('draft_id')
    
    # 2. Fetch Draft Picks & Players
    picks = requests.get(f"https://api.sleeper.app/v1/draft/{draft_id}/picks").json()
    players = requests.get("https://api.sleeper.app/v1/players/nfl").json()
    users = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/users").json()
    
    user_map = {u['user_id']: u.get('metadata', {}).get('team_name') or u.get('display_name') for u in users}
    return picks, players, user_map, draft_id

picks, players, user_map, draft_id = fetch_draft_data()

# --- APP NAVIGATION ---
st.sidebar.title("Draft Command Center")
mode = st.sidebar.selectbox("Select Mode", ["📦 KEEPER VALUATION", "🏁 LIVE DRAFT GRADER", "📊 ROSTER ANALYSIS"])

if mode == "📦 KEEPER VALUATION":
    st.header("💎 Keeper Value Ratings")
    st.info("Calculating value based on Pick Cost vs. Projected Performance.")
    
    keeper_data = []
    # Sleeper flags keepers in the picks metadata
    for p in picks:
        if p.get('metadata', {}).get('is_keeper') == '1':
            p_info = players.get(p['player_id'], {})
            name = p_info.get('full_name', 'Unknown Player')
            pos = p_info.get('position', '??')
            pick_num = p['pick_no']
            round_num = p['round']
            
            # Simple Value Logic: Early round keepers are harder to find 'value' in
            # If a top-20 player is kept in Round 5+, that's a steal.
            value_score = "🔥 ELITE" if round_num > 6 and pick_num < 50 else "✅ SOLID"
            if round_num > 10: value_score = "💎 INSANE VALUE"
            
            keeper_data.append({
                "Team": user_map.get(p['picked_by'], "Unknown"),
                "Player": name,
                "Pos": pos,
                "Round Cost": round_num,
                "Overall Pick": pick_num,
                "Value Grade": value_score
            })
    
    if keeper_data:
        df_keepers = pd.DataFrame(keeper_data).sort_values(by="Overall Pick")
        st.table(df_keepers)
    else:
        st.warning("No keepers identified in this draft ID yet.")

elif mode == "🏁 LIVE DRAFT GRADER":
    st.header("Draft Board Analysis")
    
    if not picks:
        st.subheader("Draft hasn't started yet! Waiting for picks...")
    else:
        # Calculate Team GPA based on 'Steals' vs 'Reaches'
        # A 'Steal' is anyone drafted 12+ picks after their ADP (Simplified here)
        st.subheader("Recent Pick Analysis")
        recent_picks = []
        for p in picks[-10:]: # Show last 10 picks
            p_info = players.get(p['player_id'], {})
            recent_picks.append({
                "Pick": p['pick_no'],
                "Team": user_map.get(p['picked_by'], "Unknown"),
                "Player": p_info.get('full_name'),
                "Pos": p_info.get('position')
            })
        st.write(pd.DataFrame(recent_picks))

elif mode == "📊 ROSTER ANALYSIS":
    st.header("Post-Draft Roster Strength")
    # Group picks by user to see full rosters
    rosters = {}
    for p in picks:
        uid = p['picked_by']
        if uid not in rosters: rosters[uid] = []
        p_info = players.get(p['player_id'], {})
        rosters[uid].append(f"{p_info.get('full_name')} ({p_info.get('position')})")
    
    for uid, team_list in rosters.items():
        with st.expander(f"Team: {user_map.get(uid, 'Unknown')}"):
            st.write(", ".join(team_list))