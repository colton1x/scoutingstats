"""Team Builder v2 (/scout-team-builder) — Interactive XI, Depth Gaps, Unlocked Fits & 2x Share PNG."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from services.data_store import (
    evaluate_slot_level,
    format_stat,
    get_unlocked_fits,
    load_players,
    load_team_builder_clubs,
    xy_for_field,
)
from services.share_card import generate_lineup_png

TRY_CLUBS = [(19, "Arsenal"), (9, "Manchester City"), (8, "Liverpool"), (6, "Tottenham Hotspur"), (18, "Chelsea"), (14, "Manchester United"), (3468, "Real Madrid"), (83, "Barcelona"), (503, "Bayern Munich")]
WORD = ["Thin", "Watch", "Covered"]

st.markdown("## Team Builder v2 — Squad Depth & Recruitment")
st.caption("Free Community Edition: full Squad Cover, Next-Summer horizon, unlocked Recruitment Fits, and 2x PNG Lineup Share Card.")

clubs = load_team_builder_clubs()
all_players = load_players()
by_pid: dict[int, dict[str, Any]] = {int(p["player_id"]): p for p in all_players}

if not clubs:
    st.error("Team Builder club dataset is empty.")
    st.stop()

# Initialize builder state
if "tb_club_id" not in st.session_state:
    st.session_state["tb_club_id"] = "19" if "19" in clubs else next(iter(clubs.keys()))
if "tb_swaps" not in st.session_state:
    st.session_state["tb_swaps"] = {}
if "tb_undo_stack" not in st.session_state:
    st.session_state["tb_undo_stack"] = []
if "tb_selected_slot" not in st.session_state:
    st.session_state["tb_selected_slot"] = None

# Top Club & Controls Row
avail_club_ids = [str(cid) for cid, _ in TRY_CLUBS if str(cid) in clubs]
for cid in clubs:
    if cid not in avail_club_ids:
        avail_club_ids.append(cid)

hc1, hc2, hc3, hc4 = st.columns([2.2, 1.5, 1.3, 1.2])
with hc1:
    sel_cid = st.selectbox(
        "Club",
        avail_club_ids,
        index=avail_club_ids.index(st.session_state["tb_club_id"]) if st.session_state["tb_club_id"] in avail_club_ids else 0,
        format_func=lambda cid: f"{clubs[cid]['state']['team_name']} ({clubs[cid]['context']['team'].get('league', '')})",
        key="tb_club_sel",
    )
    if sel_cid != st.session_state["tb_club_id"]:
        st.session_state["tb_club_id"] = sel_cid
        st.session_state["tb_swaps"] = {}
        st.session_state["tb_undo_stack"] = []
        st.session_state["tb_selected_slot"] = None
        st.rerun()

club_bundle = clubs[st.session_state["tb_club_id"]]
state_data = club_bundle["state"]
ctx_data = club_bundle["context"]

# Build lookup of everyone attached to this club
local_people: dict[int, dict[str, Any]] = {}
for sq in state_data.get("squad", []):
    local_people[int(sq["player_id"])] = {
        "player_id": int(sq["player_id"]), "name": sq.get("name", ""), "short": sq.get("name", "").split()[-1],
        "age": sq.get("age"), "image": sq.get("image", ""), "position": sq.get("position", ""),
        "star_rating": sq.get("star_rating"), "value": sq.get("value"), "contract_until": sq.get("contract_until"),
    }
for sl in ctx_data.get("slots", {}).values():
    for phase in ("now", "next"):
        for role in ("starter", "cover"):
            rp = (sl.get(phase) or {}).get(role)
            if rp and rp.get("player_id"):
                pid = int(rp["player_id"])
                merged = {**local_people.get(pid, {}), **rp, "player_id": pid}
                merged["short"] = merged.get("short") or (merged.get("name") or "Player").split()[-1]
                local_people[pid] = merged
for st_row in state_data.get("starters", []):
    for role in ("player", "backup"):
        rp = st_row.get(role)
        if rp and rp.get("player_id"):
            pid = int(rp["player_id"])
            merged = {**local_people.get(pid, {}), **rp, "player_id": pid}
            merged["short"] = merged.get("short") or (merged.get("name") or "Player").split()[-1]
            local_people[pid] = merged
for p in all_players:
    pid = int(p["player_id"])
    if pid not in local_people:
        local_people[pid] = {
            "player_id": pid, "name": p.get("player_name", ""), "short": p.get("player_name", "").split()[-1],
            "age": p.get("age"), "image": p.get("image_path", ""), "position": p.get("detailed_position", p.get("position", "")),
            "star_rating": round(min(5.0, max(2.5, (float(p.get("rating_avg") or 7.0) - 5.9) * 2.5)), 1),
            "value": p.get("estimated_value_eur"), "contract_until": p.get("contract_end"), "club": p.get("team_name", ""),
        }

with hc2:
    season = st.segmented_control("Horizon", ["now", "next"], format_func=lambda x: "Today" if x == "now" else "Next Summer", default="now", key="tb_season") or "now"
with hc3:
    with_cover = st.toggle("Show cover", value=True, key="tb_cover")
with hc4:
    forms = state_data.get("formations") or [state_data.get("formation", "4-2-3-1")]
    cur_form = state_data.get("formation", "4-2-3-1")
    sel_form = st.selectbox("Shape", forms, index=forms.index(cur_form) if cur_form in forms else 0, key="tb_form")

# Compute active XI & slot cover dynamically
starters = state_data.get("starters", [])
all_fields = [s["formation_field"] for s in starters]
swaps: dict[str, int] = st.session_state["tb_swaps"]

def _orig_id(f: str) -> int | None:
    if season == "next":
        st_n = ((ctx_data.get("slots") or {}).get(f, {}).get("next") or {}).get("starter")
        return int(st_n["player_id"]) if st_n and st_n.get("player_id") else None
    s = next((x for x in starters if x["formation_field"] == f), None)
    return int(s["player"]["player_id"]) if s and s.get("player") else None

def _starter_id(f: str) -> int | None:
    return int(swaps[f]) if f in swaps else _orig_id(f)

xi_ids: set[int] = {pid for f in all_fields if (pid := _starter_id(f)) is not None}

def _cover_id(f: str) -> int | None:
    cslot = (ctx_data.get("slots") or {}).get(f)
    if cslot:
        cv = (cslot.get("next" if season == "next" else "now") or {}).get("cover")
        cid = int(cv["player_id"]) if cv and cv.get("player_id") else None
        if cid and cid not in xi_ids:
            return cid
        was = _orig_id(f) if f in swaps else None
        return was if was and was not in xi_ids else None
    s = next((x for x in starters if x["formation_field"] == f), None)
    bk = s.get("backup") if s else None
    return int(bk["player_id"]) if bk and bk.get("player_id") and int(bk["player_id"]) not in xi_ids else None

slot_records: list[dict[str, Any]] = []
for s in starters:
    f = s["formation_field"]
    sid = _starter_id(f)
    cid = _cover_id(f)
    st_p = local_people.get(sid) if sid else None
    cv_p = local_people.get(cid) if cid else None
    cslot = (ctx_data.get("slots") or {}).get(f)
    lvl_obj = evaluate_slot_level(st_p, cv_p, f in swaps, cslot, season)
    x, y, cw = xy_for_field(f, all_fields)
    pos_name = (cslot or {}).get("position") or s.get("position_group", "")
    slot_records.append({
        "field": f, "pos": pos_name, "starter": st_p, "cover": cv_p,
        "level": lvl_obj["level"], "why": lvl_obj["why"], "x": x, "y": y, "cw": cw,
    })

def _put_player(target_field: str, new_pid: int) -> None:
    st.session_state["tb_undo_stack"].append(dict(st.session_state["tb_swaps"]))
    # If new_pid is already starting elsewhere, swap them
    other_field = next((r["field"] for r in slot_records if r["starter"] and int(r["starter"]["player_id"]) == new_pid), None)
    cur_pid = _starter_id(target_field)
    if other_field and other_field != target_field and cur_pid:
        st.session_state["tb_swaps"][other_field] = cur_pid
    st.session_state["tb_swaps"][target_field] = new_pid
    if st.session_state["tb_swaps"].get(target_field) == _orig_id(target_field):
        st.session_state["tb_swaps"].pop(target_field, None)
    st.session_state["tb_selected_slot"] = None

# ---- Main Split Layout: Pitch + Slot Selector | Depth & Gap/Replace Panel ----
col_pitch, col_side = st.columns([1.3, 1.15], gap="large")

with col_pitch:
    team_meta = ctx_data.get("team", {})
    crest_html = f'<img src="{html.escape(team_meta["crest"])}" style="width:36px;height:36px;object-fit:contain;">' if team_meta.get("crest") else ""
    st.markdown(
        f'<div class="ss-card" style="display:flex;align-items:center;gap:12px;padding:12px 16px;">'
        f'{crest_html}<div><h3 style="margin:0;">{html.escape(state_data["team_name"])}</h3>'
        f'<div style="font-size:12.5px;color:var(--ss-text-2);">{html.escape(sel_form)} · {html.escape(team_meta.get("league", ""))}</div></div></div>',
        unsafe_allow_html=True,
    )

    sel_f = st.session_state.get("tb_selected_slot")
    nodes_html = ""
    for rec in slot_records:
        sp = rec["starter"]
        cv = rec["cover"]
        ph = f'<img src="{html.escape(sp["image"])}" alt="">' if sp and sp.get("image") else '<span class="ss-tag">?</span>'
        nm = sp.get("short", sp.get("name", "Player")) if sp else "Add player"
        stars_v = sp.get("star_rating") if sp else None
        meta_txt = f"★{stars_v:.1f}" if stars_v else ""
        if with_cover:
            meta_txt += f" · Cv: {cv.get('short', cv.get('name', ''))}" if cv else " · No cover"
        sel_cls = " sel" if sel_f == rec["field"] else ""
        nodes_html += (
            f'<div class="tb2-node l{rec["level"]}{sel_cls}" style="left:{rec["x"]:.1f}%;top:{rec["y"]:.1f}%;">'
            f'{ph}<div class="nm">{html.escape(nm)}</div>'
            f'<div class="meta">{html.escape(meta_txt.strip(" ·"))}</div>'
            f'<span class="fl">{WORD[rec["level"]]}</span></div>'
        )

    st.markdown(
        f'<div class="tb2-pitch">'
        f'<div class="tb2-pitch-line-half"></div><div class="tb2-pitch-circle"></div>'
        f'<div class="tb2-pitch-box-top"></div><div class="tb2-pitch-box-bot"></div>'
        f'{nodes_html}</div>',
        unsafe_allow_html=True,
    )

    # Interactive slot click pills below pitch + Share Card Download
    btn_cols = st.columns(4)
    for idx, rec in enumerate(slot_records):
        sp = rec["starter"]
        label = f"{rec['pos'][:10]}: {sp.get('short', sp.get('name', 'Player')) if sp else 'Empty'}"
        if btn_cols[idx % 4].button(label, key=f"tb_pick_{rec['field']}", use_container_width=True):
            st.session_state["tb_selected_slot"] = None if sel_f == rec["field"] else rec["field"]
            st.rerun()

    png_bytes = generate_lineup_png(
        club_name=state_data["team_name"],
        formation=sel_form,
        primary_color=state_data.get("primary_color", "#E8652E"),
        secondary_color=state_data.get("secondary_color", "#FFFFFF"),
        nodes=[{
            "x": r["x"], "y": r["y"], "level": r["level"],
            "short": r["starter"].get("short", r["starter"].get("name", "Player")) if r["starter"] else "Empty",
            "stars": r["starter"].get("star_rating") if r["starter"] else None,
            "cover_short": r["cover"].get("short", r["cover"].get("name", "")) if r["cover"] else None,
        } for r in slot_records],
        with_cover=with_cover,
    )
    st.download_button(
        "📸 Download 2x Shareable Lineup Card (PNG)",
        data=png_bytes,
        file_name=f"{state_data['team_name'].lower().replace(' ', '-')}-xi.png",
        mime="image/png",
        use_container_width=True,
        type="primary",
    )

with col_side:
    if sel_f:
        rec = next(r for r in slot_records if r["field"] == sel_f)
        sp = rec["starter"]
        orig_pid = _orig_id(sel_f)
        st.markdown(f"### Replace {sp['name'] if sp else rec['pos']}")
        st.caption(f"{rec['pos']} · {WORD[rec['level']]}" + (f": {rec['why']}" if rec["why"] else ""))

        rc_top1, rc_top2 = st.columns(2)
        if orig_pid and (not sp or int(sp["player_id"]) != orig_pid):
            orig_p = local_people.get(orig_pid, {})
            if rc_top1.button(f"Put {orig_p.get('short', 'original')} back", use_container_width=True):
                _put_player(sel_f, orig_pid)
                st.rerun()
        if rc_top2.button("✕ Close", use_container_width=True):
            st.session_state["tb_selected_slot"] = None
            st.rerun()

        t_sq, t_fit, t_any = st.tabs([f"{state_data['team_name']} Squad", "Best Fits (Unlocked)", "Any Player"])
        with t_sq:
            here_id = int(sp["player_id"]) if sp else -1
            sq_list = [local_people[int(s["player_id"])] for s in state_data.get("squad", []) if int(s["player_id"]) != here_id and int(s["player_id"]) in local_people]
            for qp in sq_list[:14]:
                c1, c2 = st.columns([3.5, 1])
                in_xi = " · in XI" if int(qp["player_id"]) in xi_ids else ""
                c1.markdown(f"**{qp['name']}** · {qp.get('position', '')} · Age {qp.get('age', '')}{in_xi}")
                if c2.button("Use", key=f"tb_sq_{qp['player_id']}", use_container_width=True):
                    _put_player(sel_f, int(qp["player_id"]))
                    st.rerun()

        with t_fit:
            fits = get_unlocked_fits(st.session_state["tb_club_id"], rec["pos"], xi_ids, max_rows=8)
            for fr in fits:
                c1, c2 = st.columns([3.5, 1])
                c1.markdown(f"**{fr['name']}** ({fr.get('club', '')}, {fr.get('age', '')}) · Fit **{fr['fit']}** · {fr.get('value', '')}")
                if c2.button("Sign", key=f"tb_fit_{fr['player_id']}", use_container_width=True):
                    _put_player(sel_f, int(fr["player_id"]))
                    st.rerun()

        with t_any:
            q_any = st.text_input("Search any player in database", placeholder="Type 2+ characters...", key="tb_any_q").strip().lower()
            if len(q_any) >= 2:
                hits = [p for p in all_players if q_any in (p.get("player_name") or "").lower()][:12]
                for ap in hits:
                    c1, c2 = st.columns([3.5, 1])
                    c1.markdown(f"**{ap['player_name']}** · {ap.get('team_name', '')} · {ap.get('detailed_position', '')}")
                    if c2.button("Put", key=f"tb_any_{ap['player_id']}", use_container_width=True):
                        _put_player(sel_f, int(ap["player_id"]))
                        st.rerun()
    else:
        # Summary KPIs + Gaps (team_builder_v2.js:193-238)
        changed_cnt = len(swaps)
        top_r1, top_r2, top_r3 = st.columns([2, 1, 1])
        top_r1.markdown(f"### The XI ({'After Summer' if season == 'next' else 'Today'})")
        if changed_cnt and top_r2.button(f"Reset ({changed_cnt})", use_container_width=True):
            st.session_state["tb_undo_stack"].append(dict(swaps))
            st.session_state["tb_swaps"] = {}
            st.rerun()
        if st.session_state["tb_undo_stack"] and top_r3.button("Undo", use_container_width=True):
            st.session_state["tb_swaps"] = st.session_state["tb_undo_stack"].pop()
            st.rerun()

        stars_vals = [float(r["starter"].get("star_rating") or 0) for r in slot_records if r["starter"]]
        age_vals = [float(r["starter"].get("age") or 0) for r in slot_records if r["starter"] and r["starter"].get("age")]
        val_sum = sum(float(r["starter"].get("value") or 0) for r in slot_records if r["starter"])
        avg_stars = round(sum(stars_vals) / max(1, len(stars_vals)) * 2) / 2
        avg_age = sum(age_vals) / max(1, len(age_vals))

        st.markdown(
            f'<div class="ss-kpis">'
            f'<div class="ss-kpi"><div class="v">★ {avg_stars:.1f}</div><div class="k">Average Quality</div></div>'
            f'<div class="ss-kpi"><div class="v">{avg_age:.1f} yrs</div><div class="k">Average XI Age</div></div>'
            f'<div class="ss-kpi"><div class="v">{format_stat(val_sum, "eur")}</div><div class="k">Total XI Value</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown(f"#### Where {state_data['team_name']} are thin")
        gaps = sorted([r for r in slot_records if r["level"] < 2], key=lambda x: x["level"])
        if not gaps:
            st.success("Every slot has a starter under 30 and first-team cover. Toggle Next Summer or click a slot to simulate transfers.")
        else:
            seen_pos = set()
            for g in gaps:
                if g["pos"] in seen_pos:
                    continue
                seen_pos.add(g["pos"])
                tag_cls = "neg" if g["level"] == 0 else "warn"
                st.markdown(
                    f'<div class="ss-card"><span class="ss-tag {tag_cls}">{WORD[g["level"]]}</span> '
                    f'<strong>{html.escape(g["pos"])}</strong> — {html.escape(g["why"])}</div>',
                    unsafe_allow_html=True,
                )
                fits = get_unlocked_fits(st.session_state["tb_club_id"], g["pos"], xi_ids, max_rows=3)
                for fr in fits:
                    fc1, fc2 = st.columns([3.5, 1])
                    fc1.markdown(f"**{fr['name']}** ({fr.get('club', '')}, {fr.get('age', '')}) · Fit **{fr['fit']}**")
                    if fc2.button("Put in XI", key=f"gap_{g['field']}_{fr['player_id']}", use_container_width=True):
                        _put_player(g["field"], int(fr["player_id"]))
                        st.rerun()

# ---- Style Profile Section (team_builder_v2.js:284-303) ----
style_meta = ctx_data.get("style") or {}
if style_meta:
    st.markdown("---")
    st.markdown(f"### How {state_data['team_name']} Play vs League")
    traits = style_meta.get("traits") or []
    if traits:
        st.markdown(" · ".join([f"**{t}**" for t in traits]))
    dims = style_meta.get("dims") or []
    for d in dims:
        pct = max(3, min(97, int(d.get("pct", 50))))
        st.markdown(
            f'<div class="fx7-trait-row"><b>{html.escape(d["label"])}</b>'
            f'<div class="fx7-trait-trk"><div class="fx7-trait-dot" style="left:{pct}%"></div></div>'
            f'<span>{html.escape(d.get("hi", ""))}</span>'
            f'<span style="color:var(--ss-muted);">{d.get("rank", 1)} of {d.get("n", 20)}</span></div>',
            unsafe_allow_html=True,
        )
    alike = style_meta.get("alike") or []
    if alike:
        st.caption(f"Most stylistically similar clubs: {', '.join(alike)}")
