"""FPL Hub v2 (/fpl/) — Keyless Public FPL API Identity, Rank Sparkline, Transfers & Chip Planner."""

from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

from services.data_store import load_fpl_seed
from services.fpl_client import (
    fetch_fpl_bootstrap,
    fetch_fpl_manager_overview,
    get_demo_fpl_overview,
    parse_fpl_entry,
)

st.markdown("## FPL Hub v2 — Live Fantasy Premier League Planner")
st.caption("Uses the official keyless public FPL API (fantasy.premierleague.com). Free Edition unlocks Chip Windows & Best Transfers.")

fpl_seed = load_fpl_seed()
CHIP_NAMES = {"wildcard": "Wildcard", "freehit": "Free Hit", "bboost": "Bench Boost", "3xc": "Triple Captain"}

# ---- Identity Input Bar (fpl_identity.js) ----
ic1, ic2, ic3 = st.columns([3, 1.1, 1.3], vertical_alignment="bottom")
with ic1:
    raw_input = st.text_input(
        "FPL Team ID or Points Page URL",
        value=str(st.session_state.get("fpl_entry_id") or ""),
        placeholder="e.g. 123456 or https://fantasy.premierleague.com/entry/123456/event/11",
        key="fpl_id_box",
    )
with ic2:
    load_btn = st.button("Load My Team", type="primary", use_container_width=True, key="fpl_load_btn")
with ic3:
    demo_btn = st.button("Load Demo Squad", use_container_width=True, key="fpl_demo_btn")

if demo_btn:
    st.session_state["fpl_demo_mode"] = True
    st.session_state.pop("fpl_entry_id", None)
    st.rerun()

if load_btn:
    parsed = parse_fpl_entry(raw_input)
    if not parsed:
        st.error("Paste a valid positive numeric FPL Team ID or FPL entry URL.")
    else:
        st.session_state["fpl_demo_mode"] = False
        st.session_state["fpl_entry_id"] = parsed
        st.rerun()

overview: dict[str, Any] | None = None
if st.session_state.get("fpl_entry_id"):
    eid = int(st.session_state["fpl_entry_id"])
    with st.spinner(f"Fetching live FPL squad #{eid}..."):
        try:
            overview = fetch_fpl_manager_overview(eid)
        except Exception as exc:
            st.warning(f"Live FPL API note: {exc}. Showing demo fallback below.")
            overview = get_demo_fpl_overview()
elif st.session_state.get("fpl_demo_mode"):
    overview = get_demo_fpl_overview()

if overview:
    ent = overview["entry"]
    grade = overview.get("grade") or {}
    cap = overview.get("captain")
    bm = overview.get("best_move")
    season = overview.get("season") or {}
    chips = overview.get("chips") or {}

    st.markdown(
        f'<div class="ss-card"><div class="ss-label">Active FPL Squad · GW {ent.get("gw", fpl_seed.get("gw", ""))}</div>'
        f'<h3>{html.escape(str(ent.get("team", "Your Team")))} <span style="font-weight:500;color:var(--ss-text-2);">({html.escape(str(ent.get("manager", "")))})</span></h3>'
        f'<div class="ss-kpis">'
        f'<div class="ss-kpi"><div class="v">{grade.get("show", "–")}</div><div class="k">Squad Grade (Top {100 - int(grade.get("percentile", 50))}%)</div></div>'
        f'<div class="ss-kpi"><div class="v">{ent.get("rank", 0):,}</div><div class="k">Overall Rank</div></div>'
        f'<div class="ss-kpi"><div class="v">{ent.get("total", 0):,}</div><div class="k">Total Points</div></div>'
        f'<div class="ss-kpi"><div class="v">{season.get("bench_pts", 0)}</div><div class="k">Bench Points</div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns(2, gap="large")
    with col_left:
        if cap:
            st.markdown(f"**Captain Pick:** {cap['n']} ({cap.get('t', '')}) — **{cap.get('ep', 0):.1f} xPts**")
        if bm and bm.get("out") and bm.get("in"):
            st.markdown(f"**Best Transfer Move:** `{bm['out']['n']}` → `{bm['in']['n']}` (**+{bm['gain']:.1f} pts** over 6 GWs)")

        ranks = season.get("ranks") or []
        if len(ranks) >= 2:
            vals = [r["rank"] for r in ranks]
            mx, mn = max(vals), min(vals)
            sp = (mx - mn) or 1
            pts = " ".join([f"{i / (len(vals) - 1) * 100:.1f},{4 + (v - mn) / sp * 52:.1f}" for i, v in enumerate(vals)])
            st.markdown(
                f'<div class="ss-card"><div class="ss-label">Overall Rank Progression (GW{ranks[0]["gw"]} to GW{ranks[-1]["gw"]})</div>'
                f'<svg viewBox="0 0 100 60" preserveAspectRatio="none" style="width:100%;height:70px;">'
                f'<polyline fill="none" stroke="#E8652E" stroke-width="2.4" points="{pts}"/></svg></div>',
                unsafe_allow_html=True,
            )

    with col_right:
        st.markdown("**Chips & Timing Windows (Unlocked)**")
        used_map = {u["chip"]: u["gw"] for u in chips.get("used", [])}
        avail = set(chips.get("available", []))
        best = chips.get("best", {})
        c_cols = st.columns(2)
        for idx, ck in enumerate(["wildcard", "freehit", "bboost", "3xc"]):
            is_on = ck in avail
            st_txt = "Available" if is_on else (f"Used GW{used_map[ck]}" if ck in used_map else "Unavailable")
            tip = f" · Best GW{best[ck]['gw']}" if is_on and best.get(ck, {}).get("gw") else ""
            c_cols[idx % 2].markdown(
                f'<div class="ss-card" style="padding:10px 12px;"><span class="ss-tag {"pos" if is_on else ""}">{st_txt}</span>'
                f'<div style="font-weight:700;margin-top:4px;">{CHIP_NAMES[ck]}{html.escape(tip)}</div></div>',
                unsafe_allow_html=True,
            )

        lg = overview.get("league")
        if lg and lg.get("top"):
            st.caption(f"Mini-League: {lg.get('name', '')}")
            st.dataframe(pd.DataFrame(lg["top"])[["rank", "team", "manager", "total", "gw"]], hide_index=True, use_container_width=True)
else:
    st.info("Enter your FPL Team ID above (or click **Load Demo Squad**) to load squad grade, rank chart, chips, and best transfers.")

# ---- Global Public PL Watchlists / Captaincy / Price Risers ----
st.markdown("---")
st.markdown("### Premier League Gameweek Watch (Public Keyless FPL Bootstrap)")
boot = fetch_fpl_bootstrap()
if not boot:
    st.caption("Showing bundled club directory from `#fh2Data` (`fpl_seed.json`). Connect online to stream live Premier League player projections.")
    teams = list((fpl_seed.get("teams") or {}).values())
    if teams:
        st.dataframe(pd.DataFrame(teams)[["short", "full", "u"]], hide_index=True, use_container_width=True)
else:
    tmap = {t["id"]: t["short_name"] for t in boot.get("teams", [])}
    pmap = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
    els = boot.get("elements", [])
    rows = [{
        "Player": e["web_name"],
        "Team": tmap.get(e["team"], ""),
        "Pos": pmap.get(e["element_type"], ""),
        "Price": f"£{e['now_cost'] / 10:.1f}m",
        "Form": float(e.get("form") or 0),
        "xPts Next": float(e.get("ep_next") or 0),
        "Selected %": float(e.get("selected_by_percent") or 0),
        "Net Transfers GW": int(e.get("transfers_in_event", 0)) - int(e.get("transfers_out_event", 0)),
    } for e in els if int(e.get("minutes") or 0) > 90]

    df_fpl = pd.DataFrame(rows)
    t_cap, t_xfer, t_val = st.tabs(["Top Captaincy (xPts)", "Most Transferred In", "Top Form Value"])
    with t_cap:
        st.dataframe(df_fpl.sort_values("xPts Next", ascending=False).head(15), hide_index=True, use_container_width=True)
    with t_xfer:
        st.dataframe(df_fpl.sort_values("Net Transfers GW", ascending=False).head(15), hide_index=True, use_container_width=True)
    with t_val:
        st.dataframe(df_fpl.sort_values("Form", ascending=False).head(15), hide_index=True, use_container_width=True)
