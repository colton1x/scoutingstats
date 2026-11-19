"""Scout Hub v2 Search (/scout-hub/search) — Full Stats, Per-90, Attributes, Panel & Similarity."""

from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

from services.data_store import (
    AGROUPS,
    ATTR_LABELS,
    GROUP_LABELS,
    GROUPS,
    LENSES,
    PCT_FIELDS,
    POS,
    POS_LABELS,
    POS_LENS,
    find_similar_players,
    format_stat,
    get_lens_columns,
    load_leagues,
    load_players,
    p90key,
    record_recent_player,
    run_advanced_search,
    toggle_watchlist,
)
from services.theme import rating_badge_html

st.markdown("## Scout Hub — Player Search")
st.caption("Free Community Edition: all competitions, Per-90 projection, FM 1–20 attribute minimums, and CSV export unlocked.")

players = load_players()
leagues = load_leagues()
league_by_id = {int(lg["id"]): lg for lg in leagues}

# ---- Top Control Bar (port of scout_search_v2.js renderControls) ----
c_mode, c_group, c_pos = st.columns([1.4, 2.2, 2.0])
with c_mode:
    mode_lbl = st.segmented_control("Search by", ["Stats", "Attributes"], default="Stats", key="sr_mode")
    mode = "attr" if mode_lbl == "Attributes" else "stats"

with c_group:
    grp_opts = list(GROUP_LABELS.keys())
    default_grp = "all"
    if st.session_state.get("search_league_id"):
        default_grp = "all"
    grp_sel = st.selectbox(
        "Competition scope",
        grp_opts,
        index=grp_opts.index(default_grp),
        format_func=lambda k: GROUP_LABELS[k],
        key="sr_group",
    )

with c_pos:
    pos_sel = st.segmented_control(
        "Position",
        list(POS_LABELS.keys()),
        format_func=lambda k: POS_LABELS[k],
        default="any",
        key="sr_pos",
    ) or "any"

# Custom league picker + text filter
c_lg, c_txt, c_age = st.columns([2.4, 1.8, 1.6])
with c_lg:
    preset_ids = GROUPS.get(grp_sel)
    preselected_lg = []
    if st.session_state.get("search_league_id"):
        sid = int(st.session_state.pop("search_league_id"))
        if sid in league_by_id:
            preselected_lg = [sid]
    elif preset_ids:
        preselected_lg = [lid for lid in preset_ids if lid in league_by_id]

    picked_lgs = st.multiselect(
        "Leagues (all unlocked — leave empty for group/all)",
        options=sorted(league_by_id.keys(), key=lambda x: league_by_id[x]["label"]),
        default=preselected_lg,
        format_func=lambda lid: f"{league_by_id[lid]['label']} ({league_by_id[lid].get('country', '')})",
        key="sr_leagues_multi",
    )
    active_league_ids = picked_lgs if picked_lgs else preset_ids

with c_txt:
    init_team = st.session_state.pop("search_team_filter", "")
    team_q = st.text_input("Player or Club filter", value=init_team, placeholder="e.g. Saka, Arsenal, Romero", key="sr_team_q")

with c_age:
    age_range = st.slider("Age", 15, 42, (16, 40), key="sr_age")

# Specific detailed position chips when position != any
det_positions: list[str] | None = None
if pos_sel != "any" and POS.get(pos_sel):
    det_positions = st.multiselect(
        "Detailed positions",
        options=POS[pos_sel],
        default=POS[pos_sel],
        key=f"sr_det_{pos_sel}",
    )

# Range & attribute filters
with st.expander("Ranges, Physical, Contract & Percentile Filters", expanded=(mode == "attr")):
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        mins_range = st.slider("Minutes played", 0, 4500, (450, 4500), step=50, key="sr_mins")
        foot_sel = st.selectbox("Preferred foot", ["", "right", "left"], format_func=lambda x: "Any" if not x else x.title(), key="sr_foot")
    with rc2:
        ht_range = st.slider("Height (cm)", 155, 205, (155, 205), key="sr_ht")
        cyear_sel = st.selectbox("Contract ends by", ["", "2026", "2027", "2028"], format_func=lambda x: "Any" if not x else f"By {x}", key="sr_cyear")
    with rc3:
        mv_range = st.slider("Market value (€M)", 0, 200, (0, 200), step=5, key="sr_mv")
        free_only = st.checkbox("Free agents only (no contract)", value=False, key="sr_fa")

    pct_field, pct_min = "", 0
    attr_mins: dict[str, int] = {}
    if mode == "stats":
        pc1, pc2 = st.columns([2, 1])
        with pc1:
            pct_field = st.selectbox(
                "Percentile threshold metric (Top %)",
                [""] + [k for k, _ in PCT_FIELDS],
                format_func=lambda k: "None" if not k else dict(PCT_FIELDS)[k],
                key="sr_pct_f",
            )
        with pc2:
            pct_min = st.select_slider("Top % tier", options=[0, 50, 75, 90], format_func=lambda v: "Off" if v == 0 else f"Top {100 - v}%", key="sr_pct_v")
    else:
        st.caption("FM-Style 1–20 Attribute Minimums (derived from per-90 & match ratings)")
        attr_keys = AGROUPS["goalkeeping"] if pos_sel == "gk" else AGROUPS["all"]
        cols_at = st.columns(4)
        for idx, ak in enumerate(attr_keys):
            val = cols_at[idx % 4].slider(ATTR_LABELS.get(ak, ak), 1, 20, 1, key=f"sr_at_{ak}")
            if val > 1:
                attr_mins[ak] = val

# ---- Lens + Per-90 Toolbar (port of scout_search_v2.js:466-472) ----
tb1, tb2 = st.columns([3.5, 1.5])
if mode == "stats":
    default_lens = POS_LENS.get(pos_sel, "overview")
    with tb1:
        lens = st.segmented_control(
            "Lens",
            list(LENSES.keys()),
            default=default_lens,
            format_func=lambda k: k.title(),
            key=f"sr_lens_{pos_sel}",
        ) or "overview"
    has_p90 = any(p90key(c[0]) for c in LENSES[lens])
    with tb2:
        if has_p90:
            per_lbl = st.segmented_control("Metric scale", ["Totals", "Per 90"], default="Totals", key="sr_per") or "Totals"
            per = "p90" if per_lbl == "Per 90" else "tot"
        else:
            per = "tot"
            st.caption("Lens uses rate metrics")
    alens = "all"
else:
    lens, per = "overview", "tot"
    with tb1:
        alens = st.segmented_control(
            "Attribute group",
            ["all", "attacking", "creating", "defending", "physical"],
            default="all",
            format_func=lambda k: k.title(),
            key="sr_alens",
        ) or "all"

active_cols = get_lens_columns(lens=lens, per=per, mode=mode, pos=pos_sel, alens=alens)
sortable_keys = [c[0] for c in active_cols if c[3] != "ns"]
sc1, sc2 = st.columns([2, 1])
with sc1:
    default_sort = "rating_avg" if "rating_avg" in sortable_keys else sortable_keys[0]
    sort_by = st.selectbox(
        "Sort column",
        sortable_keys,
        index=sortable_keys.index(default_sort),
        format_func=lambda k: dict((c[0], c[1]) for c in active_cols).get(k, k),
        key="sr_sort_col",
    )
with sc2:
    sort_order = st.segmented_control("Order", ["Desc", "Asc"], default="Desc", key="sr_sort_ord") or "Desc"

filtered = run_advanced_search(
    players,
    mode=mode,
    league_ids=active_league_ids,
    team_filter=team_q,
    pos_key=pos_sel,
    detailed_positions=det_positions,
    age_min=age_range[0],
    age_max=age_range[1],
    mins_min=mins_range[0],
    mins_max=mins_range[1],
    height_min=ht_range[0],
    height_max=ht_range[1],
    value_min=mv_range[0] * 1_000_000.0,
    value_max=mv_range[1] * 1_000_000.0,
    foot=foot_sel,
    contract_year=cyear_sel,
    free_agents_only=free_only,
    pct_field=pct_field,
    pct_min=pct_min,
    attr_mins=attr_mins,
    sort_by=sort_by,
    sort_desc=(sort_order != "Asc"),
)

# ---- Main Board + Docked HubPlayerPanel ----
board_col, panel_col = st.columns([1.85, 1.15], gap="large")

with board_col:
    hdr_l, hdr_r = st.columns([2, 1])
    hdr_l.markdown(f"**{len(filtered)}** matching players")
    if filtered:
        export_df = pd.DataFrame(filtered)
        hdr_r.download_button(
            "⬇ Export CSV",
            data=export_df.to_csv(index=False).encode("utf-8"),
            file_name="scoutingstats-search.csv",
            mime="text/csv",
            use_container_width=True,
        )

    if not filtered:
        st.warning("No players match these filters. Try loosening Minutes played or changing Competition scope.")
    else:
        rows_df = []
        for rank_idx, p in enumerate(filtered, start=1):
            rec: dict[str, Any] = {
                "#": rank_idx,
                "Photo": p.get("image_path") or "",
                "Player": p.get("player_name"),
                "Club": p.get("team_name"),
                "Pos": p.get("detailed_position") or p.get("position"),
            }
            for col_k, col_lbl, kind, flags in active_cols:
                if flags == "gk" and p.get("position") != "Goalkeeper":
                    rec[col_lbl] = "–"
                elif col_k in ATTR_LABELS:
                    rec[col_lbl] = (p.get("attributes") or {}).get(col_k, 10)
                else:
                    raw_val = p.get(col_k)
                    if kind in ("n0", "n1", "n2", "n3") and raw_val is not None:
                        rec[col_lbl] = round(float(raw_val), 2 if kind == "n2" else (3 if kind == "n3" else 0))
                    else:
                        rec[col_lbl] = format_stat(raw_val, kind)
            rows_df.append(rec)

        df_show = pd.DataFrame(rows_df)
        event = st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True,
            height=560,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "Photo": st.column_config.ImageColumn("", width="small"),
                "#": st.column_config.NumberColumn("#", width="small"),
            },
        )
        if event and event.selection and event.selection.rows:
            sel_idx = event.selection.rows[0]
            chosen = filtered[sel_idx]
            st.session_state["selected_player_id"] = int(chosen["player_id"])
            record_recent_player(chosen)

with panel_col:
    # Determine player to show in HubPlayerPanel
    sel_pid = st.session_state.get("selected_player_id")
    active_p = next((p for p in filtered if int(p["player_id"]) == int(sel_pid)), None) if sel_pid else None
    if active_p is None and sel_pid:
        active_p = next((p for p in players if int(p["player_id"]) == int(sel_pid)), None)
    if active_p is None and filtered:
        active_p = filtered[0]

    if not active_p:
        st.info("Select any row from the leaderboard to inspect form, relative bars, similar profiles, and watchlists.")
    else:
        pid_int = int(active_p["player_id"])
        img_url = active_p.get("image_path") or ""
        avatar = f'<img src="{html.escape(img_url)}" style="width:52px;height:52px;border-radius:999px;object-fit:cover;background:#1e293b;">' if img_url else ""
        sub_line = f"{active_p.get('detailed_position', active_p.get('position', ''))} · {active_p.get('age', '')} yrs · {active_p.get('team_name', '')}"

        st.markdown(
            f'<div class="ss-card">'
            f'<div style="display:flex;gap:12px;align-items:center;">{avatar}'
            f'<div><div class="ss-label">{html.escape(active_p.get("league_name", "League"))}</div>'
            f'<h3 style="margin:0;">{html.escape(active_p["player_name"])}</h3>'
            f'<div style="font-size:12.5px;color:var(--ss-text-2);">{html.escape(sub_line)}</div></div></div>'
            f'<div class="ss-kpis">'
            f'<div class="ss-kpi"><div class="v">{active_p.get("games_played", 0)}</div><div class="k">Apps</div></div>'
            f'<div class="ss-kpi"><div class="v">{format_stat(active_p.get("minutes_played"), "n0")}</div><div class="k">Mins</div></div>'
            f'<div class="ss-kpi"><div class="v">{format_stat(active_p.get("rating_avg"), "n2")}</div><div class="k">Rating</div></div>'
            f'<div class="ss-kpi"><div class="v">{format_stat(active_p.get("estimated_value_eur"), "eur")}</div><div class="k">Value</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # Panel sub-tabs: Profile Bars | Similar Players | Compare | Notes & Lists
        pt_bars, pt_sim, pt_cmp, pt_list = st.tabs(["Profile", "Similar", "Compare", "Track"])

        with pt_bars:
            if mode == "attr":
                st.caption("FM-Style Attributes (1–20 scale)")
                keys = AGROUPS["goalkeeping"] if active_p.get("position") == "Goalkeeper" else AGROUPS["all"]
                attrs = active_p.get("attributes") or {}
                bars_html = ""
                for ak in sorted(keys, key=lambda x: attrs.get(x, 0), reverse=True)[:10]:
                    av = int(attrs.get(ak, 10))
                    lead_cls = " lead" if av >= 16 else ""
                    bars_html += (
                        f'<div class="hpp-bar-row"><span>{html.escape(ATTR_LABELS.get(ak, ak))}</span>'
                        f'<div class="hpp-bar-track"><div class="hpp-bar-fill{lead_cls}" style="width:{round(av / 20 * 100)}%"></div></div>'
                        f'<b style="text-align:right;">{av} / 20</b></div>'
                    )
                st.markdown(f'<div class="ss-card">{bars_html}</div>', unsafe_allow_html=True)
            else:
                st.caption(f"Lens: {lens.title()} ({'Per 90' if per == 'p90' else 'Totals'}) vs current search leader")
                lens_cols = [
                    c for c in active_cols
                    if c[2] not in ("eur", "yr") and c[0] not in ("minutes_played", "height", "games_played")
                    and (c[3] != "gk" or active_p.get("position") == "Goalkeeper")
                    and active_p.get(c[0]) is not None
                ][:8]
                bars_html = ""
                for col_k, col_lbl, kind, _ in lens_cols:
                    v = float(active_p.get(col_k) or 0)
                    col_max = max([float(x.get(col_k) or 0) for x in filtered] + [0.0001])
                    pct_w = min(100, max(0, round((v / col_max) * 100))) if col_max > 0 and v > 0 else 0
                    lead_cls = " lead" if col_max > 0 and abs(v - col_max) < 1e-6 else ""
                    bars_html += (
                        f'<div class="hpp-bar-row"><span>{html.escape(col_lbl)}</span>'
                        f'<div class="hpp-bar-track"><div class="hpp-bar-fill{lead_cls}" style="width:{pct_w}%"></div></div>'
                        f'<b style="text-align:right;">{html.escape(format_stat(v, kind))}</b></div>'
                    )
                st.markdown(f'<div class="ss-card">{bars_html}</div>', unsafe_allow_html=True)

            # Last 5 form bars (hub_player_panel.js:57-60)
            form_vals = active_p.get("form") or []
            if form_vals:
                f_cols = ""
                for fv in form_vals[-5:]:
                    ht_pct = max(12, min(100, round((float(fv) - 5.0) / 4.0 * 100)))
                    hi_cls = " hi" if float(fv) >= 7.0 else ""
                    f_cols += f'<div class="hpp-form-col"><div class="hpp-form-bar{hi_cls}" style="height:{ht_pct}%">{float(fv):.1f}</div></div>'
                st.markdown(
                    f'<div class="ss-card"><div class="ss-label">Last Five Match Ratings</div>'
                    f'<div class="hpp-form-wrap">{f_cols}</div></div>',
                    unsafe_allow_html=True,
                )

        with pt_sim:
            sims = find_similar_players(players, pid_int, top_n=6)
            if not sims:
                st.caption("Not enough positional peers to compute similarity.")
            for item in sims:
                sp = item["player"]
                sim_pct = item["similarity"]
                s_col1, s_col2 = st.columns([3.2, 1])
                s_col1.markdown(f"**{sp['player_name']}** ({sp.get('team_name', '')}) · **{sim_pct}%** match")
                if s_col2.button("Open", key=f"sim_{pid_int}_{sp['player_id']}", use_container_width=True):
                    st.session_state["selected_player_id"] = int(sp["player_id"])
                    st.rerun()

        with pt_cmp:
            peers = [p for p in players if int(p["player_id"]) != pid_int]
            other = st.selectbox(
                "Compare against",
                peers,
                format_func=lambda p: f"{p['player_name']} ({p.get('team_name', '')})",
                key=f"cmp_sel_{pid_int}",
            )
            if other:
                cmp_rows = []
                for mk, mlbl in [
                    ("rating_avg", "Avg Rating"),
                    ("goals_per90", "Goals / 90"),
                    ("assists_per90", "Assists / 90"),
                    ("xg_total_per90", "xG / 90"),
                    ("passes_key_per90", "Key Passes / 90"),
                    ("passes_accuracy_avg", "Pass Accuracy %"),
                    ("tackles_total_per90", "Tackles / 90"),
                    ("duels_won_percentage_avg", "Duels Won %"),
                ]:
                    cmp_rows.append({
                        "Metric": mlbl,
                        active_p["player_name"]: round(float(active_p.get(mk) or 0), 2),
                        other["player_name"]: round(float(other.get(mk) or 0), 2),
                    })
                st.dataframe(pd.DataFrame(cmp_rows), hide_index=True, use_container_width=True)

        with pt_list:
            st.caption("Watchlists")
            for wl_id, wl in st.session_state["watchlists"].items():
                in_wl = pid_int in wl["player_ids"]
                btn_lbl = f"✓ In {wl['name']}" if in_wl else f"+ Add to {wl['name']}"
                if st.button(btn_lbl, key=f"wl_{pid_int}_{wl_id}", use_container_width=True):
                    toggle_watchlist(wl_id, pid_int)
                    st.rerun()

            cur_note = st.session_state["player_notes"].get(pid_int, "")
            new_note = st.text_area("Scouting Note", value=cur_note, height=90, key=f"note_txt_{pid_int}")
            if st.button("Save Note", key=f"note_save_{pid_int}", type="primary"):
                st.session_state["player_notes"][pid_int] = new_note.strip()
                st.success("Note saved to Scout Desk.")
