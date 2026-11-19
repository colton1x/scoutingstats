"""FPL Hub v2 public keyless Fantasy Premier League API client & Identity resolver."""

from __future__ import annotations

import re
from typing import Any

import requests
import streamlit as st

FPL_BASE = "https://fantasy.premierleague.com/api"
HEADERS = {"User-Agent": "ScoutingStats-Streamlit-Clone/1.0"}


def parse_fpl_entry(raw: str | int | None) -> int | None:
    """Port of fpl_identity.js:74-78 parse(raw) accepting IDs or points URLs."""
    if raw is None:
        return None
    s = str(raw).strip()
    m = re.search(r"entry/(\d{1,10})(?:/|$|\?|#)", s) or re.match(r"^(\d{1,10})$", s)
    if not m:
        return None
    val = int(m.group(1))
    return val if val > 0 else None


@st.cache_data(ttl=300, show_spinner=False)
def fetch_fpl_bootstrap() -> dict[str, Any] | None:
    """Fetch public FPL static bootstrap (players, events, deadlines, team strengths)."""
    try:
        r = requests.get(f"{FPL_BASE}/bootstrap-static/", headers=HEADERS, timeout=6)
        if r.ok:
            return r.json()
    except Exception:
        return None
    return None


@st.cache_data(ttl=120, show_spinner=False)
def fetch_fpl_manager_overview(entry_id: int) -> dict[str, Any]:
    """Fetch real FPL entry summary, history & current GW picks formatted like /api/fpl/v2/me."""
    boot = fetch_fpl_bootstrap()
    if not boot:
        raise RuntimeError("Could not reach fantasy.premierleague.com API right now.")

    r_entry = requests.get(f"{FPL_BASE}/entry/{entry_id}/", headers=HEADERS, timeout=6)
    if r_entry.status_code == 404:
        raise ValueError("No FPL team found with that ID.")
    if r_entry.status_code == 429:
        raise RuntimeError("FPL API rate limit hit (429). Try again in a minute.")
    r_entry.raise_for_status()
    entry = r_entry.json()

    r_hist = requests.get(f"{FPL_BASE}/entry/{entry_id}/history/", headers=HEADERS, timeout=6)
    hist = r_hist.json() if r_hist.ok else {}

    events = boot.get("events", [])
    cur_ev = next((e for e in events if e.get("is_current")), None) or next((e for e in reversed(events) if e.get("finished")), None)
    cur_gw = cur_ev["id"] if cur_ev else (entry.get("current_event") or 1)

    r_picks = requests.get(f"{FPL_BASE}/entry/{entry_id}/event/{cur_gw}/picks/", headers=HEADERS, timeout=6)
    picks_data = r_picks.json() if r_picks.ok else {"picks": []}

    el_by_id = {e["id"]: e for e in boot.get("elements", [])}
    team_by_id = {t["id"]: t for t in boot.get("teams", [])}

    picks = picks_data.get("picks", [])
    cap_pick = next((p for p in picks if p.get("is_captain")), None)
    cap_el = el_by_id.get(cap_pick["element"], {}) if cap_pick else {}
    cap_team = team_by_id.get(cap_el.get("team"), {}).get("short_name", "")

    # Identify best transfer upgrade by ep_next within position
    squad_ids = {p["element"] for p in picks}
    best_out = None
    best_in = None
    best_gain = -1.0
    for p in picks:
        el = el_by_id.get(p["element"])
        if not el:
            continue
        et = el.get("element_type")
        ep_cur = float(el.get("ep_next") or 0)
        budget = int(el.get("now_cost") or 0) + int(entry.get("last_deadline_bank") or 0)
        for cand in boot.get("elements", []):
            if cand["id"] in squad_ids or cand.get("element_type") != et:
                continue
            if int(cand.get("now_cost") or 999) > budget:
                continue
            gain = (float(cand.get("ep_next") or 0) - ep_cur) * 4.5
            if gain > best_gain:
                best_gain = gain
                best_out = {"n": el.get("web_name", ""), "t": team_by_id.get(el.get("team"), {}).get("short_name", "")}
                best_in = {"n": cand.get("web_name", ""), "t": team_by_id.get(cand.get("team"), {}).get("short_name", "")}

    cur_hist = hist.get("current", [])
    ranks = [{"gw": g["event"], "rank": g["overall_rank"], "pts": g["points"]} for g in cur_hist if g.get("overall_rank")]
    bench_pts = sum(int(g.get("points_on_bench") or 0) for g in cur_hist)
    hits = sum(int(g.get("event_transfers_cost") or 0) for g in cur_hist)
    last_move = 0
    if len(ranks) >= 2:
        last_move = ranks[-2]["rank"] - ranks[-1]["rank"]

    used_chips = [{"chip": c["name"], "gw": c["event"]} for c in hist.get("chips", [])]
    used_names = {c["chip"] for c in used_chips}
    all_chips = ["wildcard", "freehit", "bboost", "3xc"]
    avail_chips = [c for c in all_chips if c not in used_names]

    leagues = (entry.get("leagues") or {}).get("classic", [])
    mini_league = None
    if leagues:
        user_leagues = [lg for lg in leagues if lg.get("league_type") == "x"] or leagues
        top_lg = user_leagues[0]
        mini_league = {
            "name": top_lg.get("name", "Mini-League"),
            "top": [
                {"rank": top_lg.get("entry_rank", 1), "team": entry.get("name", ""), "manager": f"{entry.get('player_first_name', '')} {entry.get('player_last_name', '')}".strip(), "total": entry.get("summary_overall_points", 0), "gw": entry.get("summary_event_points", 0), "you": True}
            ],
            "you": None,
        }

    overall_rank = entry.get("summary_overall_rank") or 1_000_000
    pct_beat = max(1, min(99, round((1 - min(overall_rank, 10_000_000) / 10_000_000) * 100)))
    grade_letter = "A+" if pct_beat >= 95 else "A" if pct_beat >= 85 else "B+" if pct_beat >= 70 else "B" if pct_beat >= 50 else "C"

    return {
        "entry": {
            "id": entry_id,
            "team": entry.get("name", f"Team {entry_id}"),
            "manager": f"{entry.get('player_first_name', '')} {entry.get('player_last_name', '')}".strip(),
            "rank": entry.get("summary_overall_rank"),
            "total": entry.get("summary_overall_points"),
            "gw": cur_gw,
        },
        "grade": {
            "show": grade_letter,
            "basis": "percentile",
            "percentile": pct_beat,
            "sample_n": 10_000_000,
        },
        "captain": {
            "n": cap_el.get("web_name", "N/A"),
            "t": cap_team,
            "ep": float(cap_el.get("ep_next") or 0),
        } if cap_el else None,
        "best_move": {
            "out": best_out,
            "in": best_in,
            "gain": round(best_gain, 1),
        } if best_out and best_in and best_gain > 0 else None,
        "season": {
            "ranks": ranks,
            "bench_pts": bench_pts,
            "hits": hits,
            "last_move": last_move,
        },
        "chips": {
            "used": used_chips,
            "available": avail_chips,
            "best": {
                "bboost": {"gw": min(38, cur_gw + 5)},
                "3xc": {"gw": min(38, cur_gw + 3), "n": cap_el.get("web_name", "Top DGW Captain")},
            },
            "locked": False,  # Analyst chip-window paywall unlocked
        },
        "league": mini_league,
        "picks": [p["element"] for p in picks],
    }


def get_demo_fpl_overview() -> dict[str, Any]:
    """Deterministic fallback FPL Hub v2 overview for instant offline exploration."""
    return {
        "entry": {"id": 42019, "team": "North London xG", "manager": "Demo Scout", "rank": 84120, "total": 742, "gw": 11},
        "grade": {"show": "A", "basis": "percentile", "percentile": 94, "sample_n": 10_850_000},
        "captain": {"n": "Saka", "t": "ARS", "ep": 8.4},
        "best_move": {"out": {"n": "Bowen", "t": "WHU"}, "in": {"n": "Palmer", "t": "CHE"}, "gain": 6.8},
        "season": {
            "ranks": [
                {"gw": 1, "rank": 1240000}, {"gw": 2, "rank": 980000}, {"gw": 3, "rank": 640000},
                {"gw": 4, "rank": 510000}, {"gw": 5, "rank": 420000}, {"gw": 6, "rank": 295000},
                {"gw": 7, "rank": 210000}, {"gw": 8, "rank": 154000}, {"gw": 9, "rank": 118000},
                {"gw": 10, "rank": 99400}, {"gw": 11, "rank": 84120},
            ],
            "bench_pts": 62,
            "hits": 8,
            "last_move": 15280,
        },
        "chips": {
            "used": [{"chip": "wildcard", "gw": 6}],
            "available": ["freehit", "bboost", "3xc"],
            "best": {"bboost": {"gw": 33}, "3xc": {"gw": 25, "n": "Haaland / Saka DGW"}},
            "locked": False,
        },
        "league": {
            "name": "Analyst Scouting Circle",
            "top": [
                {"rank": 1, "team": "xG Philosophy XI", "manager": "A. Patel", "total": 768, "gw": 74, "you": False},
                {"rank": 2, "team": "Expected Threat FC", "manager": "M.Silva", "total": 755, "gw": 69, "you": False},
                {"rank": 3, "team": "North London xG", "manager": "Demo Scout", "total": 742, "gw": 81, "you": True},
            ],
            "you": None,
        },
        "picks": [],
    }
