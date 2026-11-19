"""Live Fixtures v7 (/fixtures) — Competition Filter, 30s Auto-Poll & Poisson Inspector."""

from __future__ import annotations

import html
from datetime import date
from typing import Any

import streamlit as st

from services.fixtures_client import get_board_for_date, get_match_inspector_payload, render_momentum_svg
from services.theme import rating_badge_html

st.markdown("## Live Fixtures Board")

# Filter Toolbar (fixtures_v7.js:188-311)
fc1, fc2, fc3, fc4 = st.columns([1.3, 1.5, 1.5, 1.1])
with fc1:
    sel_date = st.date_input("Matchday Date", value=date(2026, 11, 19), key="fx_date")
with fc2:
    status_filter = st.segmented_control("Status", ["all", "live", "upcoming", "finished"], default="all", format_func=lambda s: s.title(), key="fx_status") or "all"
with fc3:
    team_search = st.text_input("Filter team", placeholder="Search team name...", key="fx_q").strip().lower()
with fc4:
    top_only = st.toggle("Top Leagues Only", value=False, key="fx_top")

auto_poll = st.toggle("Enable 30s Live Polling (@st.fragment)", value=False, key="fx_poll")

@st.fragment(run_every="30s" if auto_poll else None)
def render_fixtures_board() -> None:
    fx7, comps, is_live_api = get_board_for_date(sel_date.isoformat())
    fx_data = fx7.get("data", {})

    if is_live_api:
        st.success("Connected to live Football-Data.org v4 feed (30s edge poll active).")
    else:
        st.caption("Showing captured `scoutingstats.ai` Matchday Board & Poisson probabilities. Add `FOOTBALL_DATA_API_KEY` in Secrets for live external feeds.")

    comp_names = [f"{c['league_name']} ({c.get('country', '')})" for c in comps]
    picked_comps = st.multiselect("Competitions filter (leave empty for all)", comp_names, key="fx_comps_multi")

    visible_rows: list[dict[str, Any]] = []
    filtered_comps: list[dict[str, Any]] = []
    for c in comps:
        if top_only and not c.get("is_top"):
            continue
        cname = f"{c['league_name']} ({c.get('country', '')})"
        if picked_comps and cname not in picked_comps:
            continue
        matched = []
        for r in c.get("rows", []):
            if status_filter != "all" and r.get("status") != status_filter:
                continue
            if team_search and team_search not in r["home"].lower() and team_search not in r["away"].lower():
                continue
            matched.append(r)
            visible_rows.append(r)
        if matched:
            filtered_comps.append({**c, "rows": matched})

    if "fx_selected_fid" not in st.session_state or not any(str(r["fid"]) == str(st.session_state["fx_selected_fid"]) for r in visible_rows):
        if visible_rows:
            # Prefer live -> upcoming -> finished -> 19621738 default
            pref = next((r for r in visible_rows if str(r["fid"]) == "19621738"), None)
            if not pref:
                pref = next((r for r in visible_rows if r.get("status") == "live"), None) or visible_rows[0]
            st.session_state["fx_selected_fid"] = str(pref["fid"])

    board_col, insp_col = st.columns([1.25, 1.35], gap="large")

    with board_col:
        if not filtered_comps:
            st.warning("No fixtures match current filters.")
        for c in filtered_comps:
            st.markdown(f"#### {c['league_name']} · `{c.get('country', '')}`")
            for r in c["rows"]:
                score_str = f"{r['hs']} - {r['as']}" if r.get("hs") is not None else (r.get("st") or r.get("ko", "")[11:16])
                xg_str = f" · xG {r['home_xg']:.2f}-{r['away_xg']:.2f}" if r.get("home_xg") is not None else ""
                is_sel = str(r["fid"]) == str(st.session_state.get("fx_selected_fid"))
                lbl = f"{'▶ ' if is_sel else ''}{r['home']}   [{score_str}]   {r['away']}{xg_str}"
                if st.button(lbl, key=f"fx_row_{r['fid']}", use_container_width=True, type="primary" if is_sel else "secondary"):
                    st.session_state["fx_selected_fid"] = str(r["fid"])
                    st.rerun()

    with insp_col:
        sel_fid = str(st.session_state.get("fx_selected_fid", ""))
        active_row = next((r for r in visible_rows if str(r["fid"]) == sel_fid), None)
        if not active_row:
            st.info("Select a fixture to inspect Win Probability, xG Outlook, Form, H2H, and Lineups.")
            return

        payload = get_match_inspector_payload(active_row, fx_data.get(sel_fid))
        core = payload.get("core", {})
        entry_m = (fx_data.get(sel_fid) or {}).get("m")
        entry_o = (fx_data.get(sel_fid) or {}).get("o")

        # Hero Card
        st.markdown(
            f'<div class="ss-card"><div class="ss-label">{html.escape(core.get("league_name", ""))} · {html.escape(str(core.get("starting_at", ""))[:16].replace("T", " "))} UTC</div>'
            f'<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">'
            f'<div style="text-align:center;flex:1;"><img src="{html.escape(core.get("home_badge", ""))}" style="height:46px;"><div style="font-weight:800;margin-top:4px;">{html.escape(core.get("home_team_name", ""))}</div></div>'
            f'<div style="text-align:center;"><div style="font-size:28px;font-weight:900;">'
            f'{core.get("home_score", 0) if active_row["status"] != "upcoming" else str(core.get("starting_at", ""))[11:16]}'
            f'{" - " + str(core.get("away_score", 0)) if active_row["status"] != "upcoming" else ""}'
            f'</div><span class="ss-tag accent">{html.escape(str(core.get("status_text", active_row["status"])).upper())}</span></div>'
            f'<div style="text-align:center;flex:1;"><img src="{html.escape(core.get("away_badge", ""))}" style="height:46px;"><div style="font-weight:800;margin-top:4px;">{html.escape(core.get("away_team_name", ""))}</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # Win Probability Bar & Odds (fixtures_v7.js:460-474)
        if entry_m:
            h_p, d_p, a_p = float(entry_m.get("h", 40)), float(entry_m.get("d", 28)), float(entry_m.get("a", 32))
            odds_line = (
                f'<div style="font-size:12px;color:var(--ss-text-2);margin-top:6px;">'
                f'Odds: Home <b>{entry_o["home"]:.2f}</b> · Draw <b>{entry_o["draw"]:.2f}</b> · Away <b>{entry_o["away"]:.2f}</b></div>'
            ) if entry_o else ""
            st.markdown(
                f'<div class="ss-card"><div class="ss-label">Pre-Match Win Probability</div>'
                f'<div class="fx7-wp-bar">'
                f'<div class="fx7-wp-h" style="flex:{max(h_p, 4)};"></div>'
                f'<div class="fx7-wp-d" style="flex:{max(d_p, 4)};"></div>'
                f'<div class="fx7-wp-a" style="flex:{max(a_p, 4)};"></div></div>'
                f'<div style="display:flex;justify-content:space-between;font-size:12.5px;font-weight:700;">'
                f'<span>{html.escape(core.get("home_short_code", "H"))} {round(h_p)}%</span>'
                f'<span>Draw {round(d_p)}%</span>'
                f'<span>{html.escape(core.get("away_short_code", "A"))} {round(a_p)}%</span></div>'
                f'{odds_line}</div>',
                unsafe_allow_html=True,
            )

        # Momentum SVG or Goals Outlook
        if active_row["status"] in ("live", "finished"):
            mom = render_momentum_svg(core.get("home_team_name", "Home"), core.get("away_team_name", "Away"), payload.get("pressure"))
            if mom:
                st.markdown(mom, unsafe_allow_html=True)

        tab_prev, tab_form, tab_lu = st.tabs(["Preview / Stats", "Form & H2H", "Lineups"])
        with tab_prev:
            if entry_m:
                xg_l = entry_m.get("xg") or [1.2, 1.0]
                scores_s = " · ".join([f"{s[0]} ({round(s[1])}%)" for s in (entry_m.get("scores") or [])[:3]])
                st.markdown(
                    f'<div class="ss-kpis">'
                    f'<div class="ss-kpi"><div class="v">{xg_l[0]:.2f} - {xg_l[1]:.2f}</div><div class="k">Expected Goals</div></div>'
                    f'<div class="ss-kpi"><div class="v">{round(entry_m.get("btts", 45))}%</div><div class="k">Both Score</div></div>'
                    f'<div class="ss-kpi"><div class="v">{round(entry_m.get("o25", 45))}%</div><div class="k">Over 2.5 Goals</div></div>'
                    f'</div><div class="ss-card"><div class="ss-label">Likely Exact Scores</div><b>{html.escape(scores_s)}</b></div>',
                    unsafe_allow_html=True,
                )
            for srow in payload.get("stats") or []:
                st.markdown(f"**{srow[0]}**: {srow[1]} vs {srow[2]}")

        with tab_form:
            form_obj = payload.get("form") or {}
            for side_lbl, side_key in [(core.get("home_team_name", "Home"), "home"), (core.get("away_team_name", "Away"), "away")]:
                chips = " ".join([f'`{g.get("r", "D")} {g.get("gf", 0)}-{g.get("ga", 0)} v {g.get("opp", "")}`' for g in (form_obj.get(side_key) or [])[:5]])
                st.markdown(f"**{side_lbl} Last 5**: {chips}")

            h2h = payload.get("h2h") or {}
            if h2h.get("matches"):
                st.markdown("---")
                st.caption("Head-to-Head History")
                for hm_row in h2h["matches"][:5]:
                    st.markdown(f"`{hm_row.get('d', '')}` · **{hm_row.get('h')}** {hm_row.get('hs')}–{hm_row.get('as')} **{hm_row.get('a')}** ({hm_row.get('lg', '')})")

        with tab_lu:
            lu = payload.get("lineups")
            if not lu:
                st.info("Lineups not yet published for this fixture.")
            else:
                lu_side = st.segmented_control("Side", ["home", "away"], default="home", format_func=lambda k: core["home_team_name"] if k == "home" else core["away_team_name"], key=f"lu_side_{sel_fid}") or "home"
                side_obj = lu.get(lu_side) or {}
                st.caption(f"Formation: {side_obj.get('fm', 'N/A')} · Source: {side_obj.get('src', 'projected')}")
                for xi in side_obj.get("xi") or []:
                    st.markdown(f"`#{xi.get('no', '-')}` **{xi.get('n', '')}** · {xi.get('pos', '')} (`{xi.get('ff', '')}`)")
                if side_obj.get("out"):
                    st.markdown("**Unavailable / Injured**")
                    for out_p in side_obj["out"]:
                        st.markdown(f"- **{out_p['n']}** — {out_p.get('why', out_p.get('cat', ''))}")

render_fixtures_board()
