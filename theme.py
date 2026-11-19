"""Shared ScoutingStats v2 design tokens, layout helpers, and Global Search dialog."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from services.data_store import load_leagues, load_players, record_recent_player


def apply_theme() -> None:
    """Inject design-token CSS matching scoutingstats.ai look_plain / theme-v2."""
    is_dark = st.session_state.get("theme", "light") == "dark"

    if is_dark:
        bg_base = "#09111E"
        bg_card = "#0F1D32"
        bg_subtle = "#162640"
        border = "rgba(148, 163, 184, 0.18)"
        text_primary = "#F1F5F9"
        text_secondary = "#94A3B8"
        text_muted = "#64748B"
    else:
        bg_base = "#F8FAFC"
        bg_card = "#FFFFFF"
        bg_subtle = "#F1F5F9"
        border = "rgba(15, 23, 42, 0.10)"
        text_primary = "#0F172A"
        text_secondary = "#475569"
        text_muted = "#64748B"

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;900&family=Inter:wght@400;500;600;700;800&display=swap');

        :root {{
            --ss-accent: #E8652E;
            --ss-accent-bright: #F97316;
            --ss-navy: #0D1B2E;
            --ss-bg: {bg_base};
            --ss-card: {bg_card};
            --ss-subtle: {bg_subtle};
            --ss-border: {border};
            --ss-text: {text_primary};
            --ss-text-2: {text_secondary};
            --ss-muted: {text_muted};
            --ss-pos: #16A34A;
            --ss-warn: #D97706;
            --ss-neg: #DC2626;
        }}

        .stApp {{
            background-color: var(--ss-bg);
            color: var(--ss-text);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}

        /* Compact chrome top bar */
        .ss-topbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 16px;
            background: var(--ss-navy);
            color: #FFFFFF;
            border-radius: 12px;
            margin-bottom: 14px;
            border: 1px solid rgba(255,255,255,0.08);
        }}
        .ss-brand {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-family: 'Barlow Condensed', 'Inter', sans-serif;
            font-weight: 900;
            font-size: 22px;
            letter-spacing: 0.02em;
        }}
        .ss-brand-dot {{
            width: 10px;
            height: 10px;
            border-radius: 999px;
            background: var(--ss-accent-bright);
            display: inline-block;
        }}
        .ss-brand-sub {{
            font-family: 'Inter', sans-serif;
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 999px;
            background: rgba(249, 115, 22, 0.2);
            color: #FDBA74;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }}

        /* Reusable Scout Hub Cards */
        .ss-card {{
            background: var(--ss-card);
            border: 1px solid var(--ss-border);
            border-radius: 12px;
            padding: 16px 18px;
            margin-bottom: 12px;
        }}
        .ss-card h3, .ss-card h4 {{
            margin: 0 0 8px 0;
            color: var(--ss-text);
            font-weight: 700;
        }}
        .ss-label {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--ss-muted);
            margin-bottom: 6px;
        }}
        .ss-kpis {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
            gap: 10px;
            margin: 8px 0 14px 0;
        }}
        .ss-kpi {{
            background: var(--ss-subtle);
            border: 1px solid var(--ss-border);
            border-radius: 10px;
            padding: 10px 12px;
        }}
        .ss-kpi .v {{
            font-size: 18px;
            font-weight: 800;
            color: var(--ss-text);
            font-variant-numeric: tabular-nums;
        }}
        .ss-kpi .k {{
            font-size: 11px;
            color: var(--ss-muted);
            font-weight: 600;
        }}

        /* Rating heat & attribute tiers */
        .rt-heat {{
            display: inline-block;
            min-width: 38px;
            text-align: center;
            padding: 2px 6px;
            border-radius: 6px;
            font-weight: 800;
            font-size: 12px;
            font-variant-numeric: tabular-nums;
            color: #fff;
        }}
        .rt-x {{ background: #059669; }}
        .rt-g {{ background: #16A34A; }}
        .rt-m {{ background: #D97706; }}
        .rt-l {{ background: #DC2626; }}

        .ss-tag {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
            border: 1px solid var(--ss-border);
            background: var(--ss-subtle);
            color: var(--ss-text-2);
        }}
        .ss-tag.pos {{ background: rgba(22,163,74,0.14); color: #16A34A; border-color: rgba(22,163,74,0.3); }}
        .ss-tag.warn {{ background: rgba(217,119,6,0.14); color: #D97706; border-color: rgba(217,119,6,0.3); }}
        .ss-tag.neg {{ background: rgba(220,38,38,0.14); color: #DC2626; border-color: rgba(220,38,38,0.3); }}
        .ss-tag.accent {{ background: rgba(232,101,46,0.14); color: #E8652E; border-color: rgba(232,101,46,0.35); }}

        /* HubPlayerPanel bars (hub_player_panel.js:44-60) */
        .hpp-bar-row {{
            display: grid;
            grid-template-columns: 110px 1fr 56px;
            align-items: center;
            gap: 8px;
            margin: 6px 0;
            font-size: 12.5px;
        }}
        .hpp-bar-track {{
            height: 8px;
            background: var(--ss-subtle);
            border-radius: 999px;
            overflow: hidden;
        }}
        .hpp-bar-fill {{
            height: 100%;
            background: var(--ss-navy);
            border-radius: 999px;
        }}
        .hpp-bar-fill.lead {{ background: var(--ss-accent); }}
        .hpp-form-wrap {{
            display: flex;
            align-items: flex-end;
            gap: 8px;
            height: 76px;
            padding: 8px 4px 2px 4px;
            border-bottom: 1px solid var(--ss-border);
        }}
        .hpp-form-col {{
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-end;
            height: 100%;
        }}
        .hpp-form-bar {{
            width: 100%;
            max-width: 34px;
            border-radius: 4px 4px 0 0;
            background: #64748B;
            color: #fff;
            font-size: 10px;
            font-weight: 700;
            text-align: center;
            padding-top: 2px;
        }}
        .hpp-form-bar.hi {{ background: #16A34A; }}

        /* Team Builder v2 Pitch (team_builder_v2.js:174-192) */
        .tb2-pitch {{
            position: relative;
            width: 100%;
            height: 540px;
            background: linear-gradient(180deg, #113825 0%, #164930 50%, #113825 100%);
            border-radius: 14px;
            border: 2px solid rgba(255,255,255,0.22);
            overflow: hidden;
            margin-bottom: 12px;
        }}
        .tb2-pitch-line-half {{
            position: absolute; left: 0; right: 0; top: 50%;
            border-top: 1.5px solid rgba(255,255,255,0.24);
        }}
        .tb2-pitch-circle {{
            position: absolute; left: 50%; top: 50%;
            width: 96px; height: 96px;
            transform: translate(-50%, -50%);
            border-radius: 999px;
            border: 1.5px solid rgba(255,255,255,0.24);
        }}
        .tb2-pitch-box-top {{
            position: absolute; left: 26%; right: 26%; top: 0; height: 15%;
            border: 1.5px solid rgba(255,255,255,0.24); border-top: none;
        }}
        .tb2-pitch-box-bot {{
            position: absolute; left: 26%; right: 26%; bottom: 0; height: 15%;
            border: 1.5px solid rgba(255,255,255,0.24); border-bottom: none;
        }}
        .tb2-node {{
            position: absolute;
            transform: translate(-50%, -50%);
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 108px;
            text-align: center;
            color: #FFFFFF;
            z-index: 2;
        }}
        .tb2-node img {{
            width: 44px; height: 44px;
            border-radius: 999px;
            object-fit: cover;
            background: #0D1B2E;
            border: 2.5px solid #22C55E;
            box-shadow: 0 3px 10px rgba(0,0,0,0.45);
        }}
        .tb2-node.l1 img {{ border-color: #F59E0B; }}
        .tb2-node.l0 img {{ border-color: #EF4444; }}
        .tb2-node.sel img {{ border-color: #F97316; box-shadow: 0 0 0 4px rgba(249,115,22,0.45); }}
        .tb2-node .nm {{
            margin-top: 3px;
            font-size: 11.5px;
            font-weight: 700;
            background: rgba(13,27,46,0.88);
            padding: 1px 6px;
            border-radius: 5px;
            white-space: nowrap;
            max-width: 106px;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .tb2-node .meta {{
            font-size: 10px;
            color: #CBD5E1;
            background: rgba(13,27,46,0.72);
            padding: 0 5px;
            border-radius: 4px;
            margin-top: 1px;
        }}
        .tb2-node .fl {{
            font-size: 9.5px;
            font-weight: 800;
            text-transform: uppercase;
            padding: 0 5px;
            border-radius: 4px;
            margin-top: 2px;
        }}
        .tb2-node.l2 .fl {{ background: #16A34A; color: #fff; }}
        .tb2-node.l1 .fl {{ background: #D97706; color: #fff; }}
        .tb2-node.l0 .fl {{ background: #DC2626; color: #fff; }}

        /* Fixtures win probability & H2H bars (fixtures_v7.js:460-474) */
        .fx7-wp-bar {{
            display: flex;
            height: 10px;
            border-radius: 999px;
            overflow: hidden;
            gap: 2px;
            margin: 6px 0;
        }}
        .fx7-wp-h {{ background: #0D1B2E; }}
        .fx7-wp-d {{ background: #94A3B8; }}
        .fx7-wp-a {{ background: #E8652E; }}
        .fx7-trait-row {{
            display: grid;
            grid-template-columns: 140px 1fr 110px 80px;
            align-items: center;
            gap: 8px;
            margin: 7px 0;
            font-size: 12.5px;
        }}
        .fx7-trait-trk {{
            position: relative;
            height: 6px;
            background: var(--ss-subtle);
            border-radius: 999px;
        }}
        .fx7-trait-dot {{
            position: absolute;
            top: 50%;
            width: 12px;
            height: 12px;
            border-radius: 999px;
            background: var(--ss-accent);
            transform: translate(-50%, -50%);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def rating_badge_html(rating: float | None) -> str:
    """Return HTML pill using exact fixtures_v7.js band(r) thresholds."""
    if rating is None:
        return '<span class="ss-tag">–</span>'
    band = "x" if rating >= 8.0 else "g" if rating >= 7.0 else "m" if rating >= 6.0 else "l"
    return f'<span class="rt-heat rt-{band}">{rating:.2f}</span>'


def render_top_bar(search_page: Any = None) -> None:
    """Render shared ScoutingStats top chrome with Quick Search & Theme Switcher."""
    wl_count = sum(len(v.get("player_ids", [])) for v in st.session_state.get("watchlists", {}).values())
    fpl_id = st.session_state.get("fpl_entry_id")
    fpl_chip = f" · FPL #{fpl_id}" if fpl_id else ""

    col_brand, col_search, col_theme = st.columns([5, 3, 1.4], vertical_alignment="center")
    with col_brand:
        st.markdown(
            f'<div class="ss-topbar">'
            f'<div class="ss-brand"><span class="ss-brand-dot"></span>'
            f'<span>scoutingstats.ai</span>'
            f'<span class="ss-brand-sub">Streamlit Free Edition</span></div>'
            f'<div style="font-size:12px;color:#CBD5E1;">'
            f'Tracked: <b>{wl_count}</b>{html.escape(fpl_chip)} · Paywalls: <b>Unlocked</b>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    with col_search:
        if st.button("🔍 Search players, clubs & leagues", use_container_width=True, key="_topbar_search"):
            open_global_search_dialog(search_page=search_page)
    with col_theme:
        cur_theme = st.session_state.get("theme", "light")
        lbl = "🌙 Dark" if cur_theme == "light" else "☀️ Light"
        if st.button(lbl, use_container_width=True, key="_topbar_theme"):
            st.session_state["theme"] = "dark" if cur_theme == "light" else "light"
            st.rerun()


@st.dialog("Search players, clubs and leagues", width="large")
def open_global_search_dialog(search_page: Any = None) -> None:
    """Port of player_picker_inline.js V2 global search & league directory."""
    players = load_players()
    leagues = load_leagues()

    query = st.text_input(
        "Query",
        placeholder="Search players, clubs and leagues (e.g. Saka, Arsenal, Serie A)...",
        label_visibility="collapsed",
        key="_pp_query_input",
    ).strip()

    tab_search, tab_browse = st.tabs(["Quick Search", "Browse by League"])

    with tab_search:
        if len(query) < 2:
            recent = st.session_state.get("pp_recent_players", [])
            if recent:
                st.caption("Recent Players")
                for rp in recent[:6]:
                    c1, c2 = st.columns([4, 1.3])
                    with c1:
                        st.markdown(f"**{rp['name']}** · {rp.get('team', '')}")
                    with c2:
                        if st.button("Open", key=f"_pp_rec_{rp['player_id']}", use_container_width=True):
                            st.session_state["selected_player_id"] = rp["player_id"]
                            if search_page is not None:
                                st.switch_page(search_page)
                            else:
                                st.rerun()
            else:
                st.info("Try typing a player, club, or competition name (2+ characters).")
            return

        ql = query.lower()
        # Rank matches: prefix hits get rank 1 (strong), substring gets rank 2
        clubs_seen: dict[str, dict[str, Any]] = {}
        for p in players:
            tname = (p.get("team_name") or "").strip()
            if not tname or ql not in tname.lower():
                continue
            if tname not in clubs_seen:
                clubs_seen[tname] = {
                    "label": tname,
                    "league": p.get("league_name", ""),
                    "count": 0,
                    "rank": 1 if tname.lower().startswith(ql) else 2,
                }
            clubs_seen[tname]["count"] += 1
        clubs = sorted(clubs_seen.values(), key=lambda x: (x["rank"], -x["count"]))[:3]

        league_hits = []
        for lg in leagues:
            lbl = (lg.get("label") or "").lower()
            ctry = (lg.get("country") or "").lower()
            if ql in lbl or ql in ctry:
                league_hits.append({
                    "id": lg["id"],
                    "label": lg["label"],
                    "country": lg.get("country", ""),
                    "rank": 1 if lbl.startswith(ql) else 2,
                })
        league_hits = sorted(league_hits, key=lambda x: x["rank"])[:3]

        player_hits = [
            p for p in players
            if ql in (p.get("player_name") or "").lower() or ql in (p.get("team_name") or "").lower()
        ][:12]

        def render_clubs() -> None:
            if not clubs:
                return
            st.caption("Clubs")
            for idx, cl in enumerate(clubs):
                c1, c2 = st.columns([4, 1.3])
                c1.markdown(f"**{cl['label']}** · {cl['league']} ({cl['count']} players indexed)")
                if c2.button("Filter", key=f"_pp_cl_{idx}_{cl['label']}", use_container_width=True):
                    st.session_state["search_team_filter"] = cl["label"]
                    if search_page is not None:
                        st.switch_page(search_page)
                    else:
                        st.rerun()

        def render_leagues() -> None:
            if not league_hits:
                return
            st.caption("Leagues")
            for idx, lg in enumerate(league_hits):
                c1, c2 = st.columns([4, 1.3])
                c1.markdown(f"**{lg['label']}** · {lg['country']}")
                if c2.button("View", key=f"_pp_lg_{idx}_{lg['id']}", use_container_width=True):
                    st.session_state["search_league_id"] = lg["id"]
                    if search_page is not None:
                        st.switch_page(search_page)
                    else:
                        st.rerun()

        def render_players() -> None:
            if not player_hits:
                return
            st.caption(f"Players ({len(player_hits)})")
            for p in player_hits:
                c1, c2 = st.columns([4, 1.3])
                c1.markdown(
                    f"**{p['player_name']}** · {p.get('detailed_position', p.get('position', ''))} "
                    f"· {p.get('age', '')} yrs · {p.get('team_name', '')}"
                )
                if c2.button("Inspect", key=f"_pp_pl_{p['player_id']}", use_container_width=True):
                    record_recent_player(p)
                    st.session_state["selected_player_id"] = p["player_id"]
                    if search_page is not None:
                        st.switch_page(search_page)
                    else:
                        st.rerun()

        strong_clubs = bool(clubs and clubs[0]["rank"] <= 1)
        strong_leagues = bool(league_hits and league_hits[0]["rank"] <= 1)

        if not clubs and not league_hits and not player_hits:
            st.warning("Nothing matches that.")
        else:
            if strong_clubs or not player_hits:
                render_clubs()
            if strong_leagues or not player_hits:
                render_leagues()
            render_players()
            if player_hits and not strong_clubs:
                render_clubs()
            if player_hits and not strong_leagues:
                render_leagues()

    with tab_browse:
        dir_filter = st.text_input("Filter leagues or countries", key="_pp_dir_filter").strip().lower()
        filtered_lgs = [
            lg for lg in leagues
            if not dir_filter or dir_filter in (lg.get("label") or "").lower() or dir_filter in (lg.get("country") or "").lower()
        ]
        st.caption(f"Showing {min(len(filtered_lgs), 40)} of {len(filtered_lgs)} unlocked competitions")
        for lg in filtered_lgs[:40]:
            c1, c2 = st.columns([4, 1.5])
            c1.markdown(f"**{lg['label']}** — {lg.get('country', '')} ({lg.get('region', 'World')})")
            if c2.button("Open Search", key=f"_pp_dir_{lg['id']}", use_container_width=True):
                st.session_state["search_league_id"] = lg["id"]
                if search_page is not None:
                    st.switch_page(search_page)
                else:
                    st.rerun()
