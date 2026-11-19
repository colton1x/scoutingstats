"""scoutingstats.ai Free Streamlit Clone — Entrypoint & Multipage Router."""

from __future__ import annotations

import streamlit as st

from services.data_store import init_app_state
from services.theme import apply_theme, render_top_bar

st.set_page_config(
    page_title="scoutingstats.ai — Football Scouting, Team Builder, Fixtures & FPL",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_app_state()
apply_theme()

home_page = st.Page("views/home.py", title="Home", icon="🏟️", url_path="", default=True)
desk_page = st.Page("views/scout_desk.py", title="Scout Desk", icon="📋", url_path="scout-hub")
search_page = st.Page("views/scout_search.py", title="Player Search", icon="🔎", url_path="scout-hub-search")
builder_page = st.Page("views/team_builder.py", title="Team Builder", icon="🧩", url_path="scout-team-builder")
fixtures_page = st.Page("views/fixtures.py", title="Fixtures", icon="📅", url_path="fixtures")
fpl_page = st.Page("views/fpl_hub.py", title="FPL Hub", icon="📊", url_path="fpl")

st.session_state["_nav_pages"] = {
    "home": home_page,
    "desk": desk_page,
    "search": search_page,
    "builder": builder_page,
    "fixtures": fixtures_page,
    "fpl": fpl_page,
}

pg = st.navigation([home_page, search_page, builder_page, fixtures_page, fpl_page, desk_page], position="top")
render_top_bar(search_page=search_page)

with st.sidebar:
    st.markdown("### ScoutingStats Cloud")
    st.caption("100% Free & Paywall-Free Recreation")
    st.markdown(
        "- **Player Search**: 8 lenses, Per-90 toggle, FM 1–20 attributes & CSV export\n"
        "- **Team Builder**: Squad depth pitch (`Thin / Watch / Covered`), unlocked fits & 2x PNG share card\n"
        "- **Fixtures**: Model win probabilities, xG outlook & minute-by-minute momentum\n"
        "- **FPL Hub**: Real public FPL API sync + Chip Planner\n"
        "- **Scout Desk**: Watchlists, Briefs & Scouting Notes"
    )
    st.divider()
    try:
        has_fd = bool(st.secrets.get("FOOTBALL_DATA_API_KEY", ""))
    except Exception:
        has_fd = False
    st.markdown(
        f"**Live Data Status**\n"
        f"- FPL Public API: 🟢 Keyless Active\n"
        f"- Football-Data API: {'🟢 Live' if has_fd else '🟡 Seed Mode (Optional Key)'}\n"
        f"- Persistence: Session / JSON Export"
    )

pg.run()
