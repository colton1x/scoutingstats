"""Scout Desk v2 (/scout-hub/) — Watch Schedule, Breakouts, Assignment Briefs & Notes."""

from __future__ import annotations

import html
import json
from typing import Any

import pandas as pd
import streamlit as st

from services.data_store import load_players, load_scout_desk_seed

st.markdown("## Scout Desk v2 — Watch Schedule & Pipeline")
st.caption("Free Community Edition: manage watchlists, Tracked-Player watch schedule, assignment briefs, and export/import portable JSON backups.")

desk_seed = load_scout_desk_seed()
players = load_players()
by_pid = {int(p["player_id"]): p for p in players}

# ---- Top KPIs & Window Toggle ----
wc1, wc2 = st.columns([2.2, 2.8])
with wc1:
    win_opt = st.segmented_control("Watch window", ["2", "7"], default="7", format_func=lambda w: "Next 48 hours" if w == "2" else "Next 7 days", key="dk_window") or "7"

schedule = desk_seed.get("schedule") or []
tracked_all = {pid for wl in st.session_state["watchlists"].values() for pid in wl["player_ids"]}
with wc2:
    k1, k2, k3 = st.columns(3)
    k1.metric("Tracked Players", len(tracked_all))
    k2.metric("Scheduled Fixtures", len(schedule))
    k3.metric("Active Briefs", len(st.session_state["assignments"]))

# ---- Main Split: Watch Schedule Board | Fixture Player Inspector ----
col_sched, col_insp = st.columns([1.35, 1.0], gap="large")

if "dk_selected_fid" not in st.session_state and schedule:
    st.session_state["dk_selected_fid"] = str(schedule[0]["id"])

with col_sched:
    st.markdown("### Watch Schedule")
    for fix in schedule:
        ps = fix.get("players") or []
        p_names = ", ".join([p["name"] for p in ps[:2]]) + (f" +{len(ps) - 2} more" if len(ps) > 2 else "")
        is_sel = str(fix["id"]) == str(st.session_state.get("dk_selected_fid"))
        lbl = f"{'▶ ' if is_sel else ''}{fix['ko'][:16].replace('T', ' ')} · {fix['home']} v {fix['away']} ({fix['league']}) — [{p_names}]"
        if st.button(lbl, key=f"dk_row_{fix['id']}", use_container_width=True, type="primary" if is_sel else "secondary"):
            st.session_state["dk_selected_fid"] = str(fix["id"])
            st.rerun()

    # Breakout players to check (captured from /api/scout-hub/v2/desk `check`)
    check_list = desk_seed.get("check") or []
    if check_list:
        st.markdown("### Players to Check (U22 Rated 7.5+)")
        for ck in check_list:
            c_left, c_right = st.columns([3.5, 1])
            c_left.markdown(f"**{ck['name']}** ({ck['age']} yrs, {ck['team']}) · **{ck['rating']:.2f}** vs {ck['opp']} ({ck['g']}G {ck['a']}A)")
            if c_right.button("Inspect", key=f"dk_chk_{ck['id']}", use_container_width=True):
                st.session_state["selected_player_id"] = int(ck["id"])
                st.switch_page(st.session_state["_nav_pages"]["search"])

with col_insp:
    sel_fid = str(st.session_state.get("dk_selected_fid", ""))
    fix = next((f for f in schedule if str(f["id"]) == sel_fid), None)
    if fix:
        st.markdown(
            f'<div class="ss-card"><div class="ss-label">{html.escape(fix.get("league", ""))} · {html.escape(fix["ko"][:16].replace("T", " "))} UTC</div>'
            f'<h4>{html.escape(fix["home"])} vs {html.escape(fix["away"])}</h4></div>',
            unsafe_allow_html=True,
        )
        for p in fix.get("players") or []:
            out_badge = f'<span class="ss-tag neg">{html.escape(p["out"]["reason"])}</span>' if p.get("out") else '<span class="ss-tag pos">Fit</span>'
            stage_badge = f'<span class="ss-tag accent">{html.escape(p.get("stage", "watching").title())}</span>'
            st.markdown(
                f'<div class="ss-card" style="padding:12px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<b>{html.escape(p["name"])}</b><div>{stage_badge} {out_badge}</div></div>'
                f'<div style="font-size:12px;color:var(--ss-text-2);margin-top:4px;">'
                f'{html.escape(p.get("pos", ""))} · {p.get("age", "")} yrs · {html.escape(p.get("team", ""))} · Avg L5: <b>{p.get("avg", 0):.2f}</b></div></div>',
                unsafe_allow_html=True,
            )

# ---- Four Desk Cards: Briefs, Needs a Look, Watchlists, Notes ----
st.markdown("---")
dc1, dc2 = st.columns(2, gap="large")

with dc1:
    st.markdown("### Scouting Briefs & Pipeline")
    for aid, b in st.session_state["assignments"].items():
        stages = b.get("stages") or {}
        st.markdown(
            f'<div class="ss-card"><div class="ss-label">Due {html.escape(b.get("deadline", ""))} · {len(stages)} candidates</div>'
            f'<h4>{html.escape(b["name"])}</h4></div>',
            unsafe_allow_html=True,
        )
        for pid, stg in list(stages.items()):
            p = by_pid.get(int(pid), {"player_name": f"Player #{pid}"})
            new_stg = st.selectbox(
                p["player_name"],
                ["identified", "watching", "assessed", "recommended"],
                index=["identified", "watching", "assessed", "recommended"].index(stg) if stg in ["identified", "watching", "assessed", "recommended"] else 0,
                key=f"asg_stage_{aid}_{pid}",
            )
            stages[pid] = new_stg

    st.markdown("### Needs a Look (Availability & Form Flags)")
    for nd in desk_seed.get("needs") or []:
        cls = "neg" if nd.get("kind") == "neg" else "pos"
        st.markdown(f'<div class="ss-card" style="padding:10px 14px;"><span class="ss-tag {cls}">Flag</span> <b>{html.escape(nd["name"])}</b> — {html.escape(nd["reason"])}</div>', unsafe_allow_html=True)

with dc2:
    st.markdown("### Watchlists & Portable JSON Backup")
    for wl_id, wl in st.session_state["watchlists"].items():
        with st.expander(f"{wl['name']} ({len(wl['player_ids'])} players)", expanded=True):
            for pid in wl["player_ids"]:
                pl = by_pid.get(int(pid), {"player_name": f"Player #{pid}", "team_name": ""})
                st.markdown(f"- **{pl['player_name']}** ({pl.get('team_name', '')})")

    st.markdown("### Recent Scouting Notes")
    for pid, note_txt in st.session_state["player_notes"].items():
        pl = by_pid.get(int(pid), {"player_name": f"Player #{pid}"})
        st.markdown(f"**{pl['player_name']}**: {note_txt}")

    backup_payload = json.dumps({
        "watchlists": st.session_state["watchlists"],
        "assignments": st.session_state["assignments"],
        "player_notes": st.session_state["player_notes"],
    }, indent=2)
    st.download_button(
        "⬇ Export Watchlists & Notes (JSON)",
        data=backup_payload.encode("utf-8"),
        file_name="scoutingstats-workspace.json",
        mime="application/json",
        use_container_width=True,
    )
