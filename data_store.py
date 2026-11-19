"""Central data loader and analytical engines ported from scout_search_v2.js and team_builder_v2.js."""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# ---- Exact constants ported from scout_search_v2.js ----
GROUPS: dict[str, list[int] | None] = {
    "all": None,
    "pl": [8],
    "top5": [8, 564, 384, 82, 301],
    "top10": [8, 564, 384, 82, 301, 72, 462, 208, 600, 501],
    "england": [8, 9, 12, 14],
    "tier2": [9, 567, 387, 85, 304],
    "scan": [271, 444, 573],
    "sa": [648, 636],
}

GROUP_LABELS: dict[str, str] = {
    "all": "All Leagues",
    "pl": "Premier League",
    "top5": "Top 5",
    "top10": "Top 10",
    "england": "England",
    "tier2": "2nd tiers",
    "scan": "Scandinavia",
    "sa": "South America",
}

POS: dict[str, list[str] | None] = {
    "any": None,
    "gk": ["Goalkeeper"],
    "def": ["Centre Back", "Left Back", "Right Back"],
    "mid": ["Defensive Midfield", "Central Midfield", "Attacking Midfield", "Left Midfield", "Right Midfield"],
    "att": ["Left Wing", "Right Wing", "Centre Forward", "Secondary Striker"],
}

POS_LABELS = {"any": "Any", "gk": "GK", "def": "DEF", "mid": "MID", "att": "ATT"}
POS_LENS = {"gk": "goalkeeping", "def": "defending", "mid": "passing", "att": "attacking"}

LENSES: dict[str, list[tuple[str, str, str, str]]] = {
    "overview": [
        ("games_played", "GP", "n0", ""),
        ("goals_total", "G", "n0", ""),
        ("assists_total", "A", "n0", ""),
        ("xg_total_total", "xG", "n2", ""),
        ("passes_key_total", "KP", "n0", ""),
        ("touches_total", "Tch", "n0", ""),
        ("passes_accuracy_avg", "Pass%", "pct", ""),
        ("duels_won_percentage_avg", "Duel%", "pct", ""),
        ("tackles_total_total", "Tkl", "n0", ""),
        ("height", "Ht", "n0", ""),
        ("contract_end", "End", "yr", "ns"),
        ("estimated_value_eur", "Value", "eur", ""),
    ],
    "attacking": [
        ("goals_total", "G", "n0", ""),
        ("assists_total", "A", "n0", ""),
        ("xg_total_total", "xG", "n2", ""),
        ("xgot_total", "xGOT", "n2", ""),
        ("shots_total_total", "Sh", "n0", ""),
        ("shots_on_target_total", "SoT", "n0", ""),
        ("big_chances_created_total", "BCC", "n0", ""),
        ("big_chances_missed_total", "BCM", "n0", ""),
        ("dribbles_attempts_total", "DrA", "n0", ""),
        ("dribbles_success_total", "DrS", "n0", ""),
        ("dribble_success_rate_avg", "Dr%", "pct", ""),
        ("penalty_scored_total", "PenS", "n0", ""),
        ("hit_woodwork_total", "Wood", "n0", ""),
        ("xg_per_shot", "xG/Sh", "n2", ""),
        ("goal_conversion_rate", "Conv%", "pct", ""),
        ("shot_accuracy", "ShAcc%", "pct", ""),
        ("goals_minus_xg", "G-xG", "sgn", ""),
        ("xg_per_touch", "xG/Tch", "n3", ""),
        ("successful_dribbles_per_touch", "Dr/Tch", "n2", ""),
        ("key_passes_per_touch", "KP/Tch", "n2", ""),
        ("goal_contributions_per90", "G+A/90", "n2", ""),
    ],
    "passing": [
        ("passes_total_total", "Pass", "n0", ""),
        ("passes_accurate_total", "Acc", "n0", ""),
        ("passes_accuracy_avg", "Pass%", "pct", ""),
        ("passes_key_total", "KP", "n0", ""),
        ("crosses_total_total", "Crs", "n0", ""),
        ("crosses_accuracy_total", "CrsA", "n0", ""),
        ("through_balls_total", "ThB", "n0", ""),
        ("through_ball_accuracy", "ThB%", "pct", ""),
        ("long_balls_total", "LgB", "n0", ""),
        ("long_balls_won_total", "LgW", "n0", ""),
        ("passes_in_final_third_total", "F3", "n0", ""),
        ("final_third_pass_rate", "F3%", "pct", ""),
    ],
    "defending": [
        ("tackles_total_total", "Tkl", "n0", ""),
        ("interceptions_total", "Int", "n0", ""),
        ("clearances_total", "Clr", "n0", ""),
        ("blocks_total_total", "Blk", "n0", ""),
        ("duels_total_total", "Duel", "n0", ""),
        ("duels_won_total", "DlW", "n0", ""),
        ("duels_won_percentage_avg", "Dl%", "pct", ""),
        ("aerials_won_total", "AerW", "n0", ""),
        ("aerials_lost_total", "AerL", "n0", ""),
        ("aerials_won_percentage_avg", "Aer%", "pct", ""),
        ("dribbled_past_total", "DrP", "n0", ""),
        ("padj_defensive_actions_per90", "PAdj Def/90", "n2", ""),
    ],
    "physical": [
        ("duels_total_total", "Duel", "n0", ""),
        ("duels_won_total", "DlW", "n0", ""),
        ("duels_won_percentage_avg", "Dl%", "pct", ""),
        ("aerials_won_total", "AerW", "n0", ""),
        ("aerials_lost_total", "AerL", "n0", ""),
        ("aerials_won_percentage_avg", "Aer%", "pct", ""),
        ("touches_total", "Tch", "n0", ""),
        ("dispossessed_total", "Disp", "n0", ""),
        ("turn_over_total", "TO", "n0", ""),
    ],
    "discipline": [
        ("fouls_committed_total", "Fls", "n0", ""),
        ("fouls_drawn_total", "FlD", "n0", ""),
        ("yellow_cards_total", "YC", "n0", ""),
        ("red_cards_total", "RC", "n0", ""),
        ("offsides_total", "Off", "n0", ""),
        ("penalty_committed_total", "PenC", "n0", ""),
        ("penalty_won_total", "PenW", "n0", ""),
    ],
    "context": [
        ("minutes_share_pct", "Min share", "pct", ""),
        ("starts_pct", "Starts%", "pct", ""),
        ("pass_involvement_pct", "Pass inv%", "pct", ""),
        ("padj_tackles_per90", "PAdj Tkl/90", "n2", ""),
        ("padj_interceptions_per90", "PAdj Int/90", "n2", ""),
        ("padj_defensive_actions_per90", "PAdj Def/90", "n2", ""),
        ("tackle_win_rate", "Tkl win%", "pct", ""),
        ("npxg_per_shot", "npxG/Sh", "n2", ""),
    ],
    "goalkeeping": [
        ("saves_total", "Svs", "n0", "gk"),
        ("save_pct", "Sv%", "pct", "gk"),
        ("gk_goals_prevented", "Prev", "sgn", "gk"),
        ("passes_accuracy_avg", "Pass%", "pct", ""),
        ("long_balls_total", "LgB", "n0", ""),
        ("clearances_total", "Clr", "n0", ""),
    ],
}

P90 = {
    "goals_per90", "assists_per90", "shots_total_per90", "shots_on_target_per90",
    "dribbles_attempts_per90", "dribbles_success_per90", "passes_total_per90",
    "passes_accurate_per90", "passes_key_per90", "tackles_total_per90",
    "blocks_total_per90", "interceptions_per90", "duels_total_per90",
    "duels_won_per90", "aerials_won_per90", "aerials_lost_per90",
    "fouls_committed_per90", "fouls_drawn_per90", "yellow_cards_per90",
    "red_cards_per90", "offsides_per90", "saves_per90", "penalty_won_per90",
    "penalty_scored_per90", "penalty_committed_per90", "crosses_total_per90",
    "crosses_accuracy_per90", "dispossessed_per90", "hit_woodwork_per90",
    "xg_total_per90", "xgot_per90", "through_balls_per90", "long_balls_per90",
    "long_balls_won_per90", "dribbled_past_per90", "turn_over_per90",
    "big_chances_created_per90", "big_chances_missed_per90", "touches_per90",
    "clearances_per90", "passes_in_final_third_per90",
}

ATTR_LABELS: dict[str, str] = {
    "finishing": "Finishing", "goal_threat": "Goal threat", "dribbling": "Dribbling",
    "decisive": "Decisive", "control": "Control", "creativity": "Creativity",
    "short_passing": "Short passing", "long_passing": "Long passing",
    "crossing": "Crossing", "ball_retention": "Retention",
    "ball_winning": "Ball winning", "def_positioning": "Positioning",
    "aggression": "Aggression", "aerial": "Aerial", "physical": "Physical",
    "stamina": "Stamina", "shot_stopping": "Shot stopping",
    "aerial_reach": "Aerial reach", "command": "Command",
    "gk_distribution": "Distribution",
}

AGROUPS: dict[str, list[str]] = {
    "all": [
        "finishing", "goal_threat", "dribbling", "decisive", "control",
        "creativity", "short_passing", "long_passing", "crossing",
        "ball_retention", "ball_winning", "def_positioning", "aggression",
        "aerial", "physical", "stamina",
    ],
    "attacking": ["finishing", "goal_threat", "dribbling", "decisive", "control"],
    "creating": ["creativity", "short_passing", "long_passing", "crossing", "ball_retention"],
    "defending": ["ball_winning", "def_positioning", "aggression", "aerial"],
    "physical": ["physical", "stamina", "aerial", "aggression"],
    "goalkeeping": ["shot_stopping", "aerial_reach", "command", "gk_distribution", "short_passing", "long_passing"],
}

PCT_FIELDS: list[tuple[str, str]] = [
    ("goals_per90", "Goals/90"), ("assists_per90", "Assists/90"),
    ("xg_total_per90", "xG/90"), ("passes_key_per90", "Key passes/90"),
    ("dribbles_success_per90", "Dribbles/90"), ("tackles_total_per90", "Tackles/90"),
    ("interceptions_per90", "Interceptions/90"), ("duels_won_per90", "Duels won/90"),
    ("aerials_won_per90", "Aerials won/90"), ("padj_tackles_per90", "PAdj tackles"),
    ("padj_interceptions_per90", "PAdj interceptions"), ("touches_per90", "Touches/90"),
    ("rating_avg", "Rating"),
]


def _read_json(filename: str, default: Any) -> Any:
    path = DATA_DIR / filename
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


@st.cache_data(show_spinner=False)
def load_players() -> list[dict[str, Any]]:
    """Return normalized players list cached across sessions."""
    return _read_json("players.json", [])


@st.cache_data(show_spinner=False)
def load_leagues() -> list[dict[str, Any]]:
    """Return all unlocked competitions from browse directory."""
    raw = _read_json("leagues_dir.json", {"items": []})
    return raw.get("items", [])


@st.cache_data(show_spinner=False)
def load_nationalities() -> list[dict[str, Any]]:
    return _read_json("nationalities.json", [])


@st.cache_data(show_spinner=False)
def load_team_builder_clubs() -> dict[str, dict[str, Any]]:
    return _read_json("team_builder_clubs.json", {})


@st.cache_data(show_spinner=False)
def load_scout_desk_seed() -> dict[str, Any]:
    return _read_json("scout_desk.json", {})


@st.cache_data(show_spinner=False)
def load_fpl_seed() -> dict[str, Any]:
    return _read_json("fpl_seed.json", {})


def p90key(col_key: str) -> str | None:
    """Port of scout_search_v2.js:40 — resolve real per-90 column key if available."""
    if not col_key.endswith("_total"):
        return None
    cand = col_key[: -len("_total")] + "_per90"
    return cand if cand in P90 else None


def format_stat(v: Any, kind: str) -> str:
    """Port of scout_search_v2.js:107-118."""
    if v is None or v == "":
        return "–"
    if kind == "yr":
        return str(v)[:4]
    try:
        fv = float(v)
    except (TypeError, ValueError):
        return str(v)
    if math.isnan(fv):
        return "–"
    if kind == "eur":
        if fv >= 1e6:
            return f"€{fv / 1e6:.0f}m" if fv >= 1e7 else f"€{fv / 1e6:.1f}m"
        if fv >= 1e3:
            return f"€{round(fv / 1e3)}k"
        return f"€{round(fv)}"
    if kind in ("n0", "att"):
        return str(round(fv))
    if kind == "n1":
        return f"{fv:.1f}"
    if kind == "n3":
        return f"{fv:.3f}"
    if kind == "pct":
        return f"{round(fv)}%"
    if kind == "sgn":
        return f"{'+' if fv > 0 else ''}{fv:.1f}"
    return f"{fv:.2f}"


def get_lens_columns(lens: str, per: str = "tot", mode: str = "stats", pos: str = "any", alens: str = "all") -> list[tuple[str, str, str, str]]:
    """Return active column specs for Stats or Attributes board mode."""
    if mode == "attr":
        keys = AGROUPS["goalkeeping"] if pos == "gk" else AGROUPS["all" if alens == "goalkeeping" else alens]
        return [("age", "Age", "n0", "ns"), ("height", "Ht", "n0", "ns")] + [
            (k, ATTR_LABELS.get(k, k), "att", "") for k in keys
        ]
    base = [("minutes_played", "Mins", "n0", ""), ("rating_avg", "Rating", "n2", "")]
    cols = []
    for k, lbl, kind, flags in LENSES.get(lens, LENSES["overview"]):
        if per == "p90" and kind in ("n0", "n2"):
            pk = p90key(k)
            if pk:
                cols.append((pk, f"{lbl}/90", "n2", flags))
                continue
        cols.append((k, lbl, kind, flags))
    return base + cols


def run_advanced_search(
    players: list[dict[str, Any]],
    *,
    mode: str = "stats",
    league_ids: list[int] | None = None,
    team_filter: str = "",
    pos_key: str = "any",
    detailed_positions: list[str] | None = None,
    age_min: int | None = None,
    age_max: int | None = None,
    mins_min: int = 0,
    mins_max: int = 9999,
    height_min: int = 155,
    height_max: int = 205,
    value_min: float = 0.0,
    value_max: float = 200_000_000.0,
    foot: str = "",
    contract_year: str = "",
    free_agents_only: bool = False,
    pct_field: str = "",
    pct_min: int = 0,
    attr_mins: dict[str, int] | None = None,
    sort_by: str = "rating_avg",
    sort_desc: bool = True,
) -> list[dict[str, Any]]:
    """Filter, rank by percentile threshold, and sort players without tier locks."""
    results: list[dict[str, Any]] = []
    pos_allowed = set(detailed_positions) if detailed_positions else (set(POS[pos_key]) if POS.get(pos_key) else None)
    lg_set = set(league_ids) if league_ids else None
    tl = team_filter.strip().lower()

    # Precompute percentile cutoff if needed across active cohort
    pct_cutoff: float | None = None
    if mode == "stats" and pct_field and pct_min > 0:
        vals = [float(p[pct_field]) for p in players if p.get(pct_field) is not None]
        if vals:
            pct_cutoff = float(np.percentile(vals, pct_min))

    for p in players:
        if lg_set and p.get("league_id") not in lg_set:
            continue
        if tl and tl not in (p.get("team_name") or "").lower() and tl not in (p.get("player_name") or "").lower():
            continue
        if pos_allowed:
            dp = p.get("detailed_position") or p.get("position")
            if dp not in pos_allowed and p.get("position") not in pos_allowed:
                continue
        age = p.get("age")
        if age_min is not None and (age is None or age < age_min):
            continue
        if age_max is not None and (age is None or age > age_max):
            continue
        mins = float(p.get("minutes_played") or 0)
        if mins < mins_min or (mins_max < 9999 and mins > mins_max):
            continue
        ht = int(p.get("height") or 180)
        if ht < height_min or (height_max < 205 and ht > height_max):
            continue
        mv = float(p.get("estimated_value_eur") or 0)
        if mv < value_min or (value_max < 200_000_000 and mv > value_max):
            continue
        if foot and (p.get("preferred_foot") or "").lower() != foot.lower():
            continue
        if contract_year:
            ce = str(p.get("contract_end") or "")
            if not ce or ce[:4] > contract_year:
                continue
        if free_agents_only and p.get("contract_end"):
            continue
        if pct_cutoff is not None:
            pv = p.get(pct_field)
            if pv is None or float(pv) < pct_cutoff:
                continue
        if mode == "attr" and attr_mins:
            attrs = p.get("attributes") or {}
            if any(int(attrs.get(k, 0)) < req for k, req in attr_mins.items() if req > 1):
                continue
        results.append(p)

    def _sort_val(item: dict[str, Any]) -> float:
        if sort_by in ATTR_LABELS:
            return float((item.get("attributes") or {}).get(sort_by, 0))
        val = item.get(sort_by)
        if val is None:
            return -1e9 if sort_desc else 1e9
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0

    results.sort(key=_sort_val, reverse=sort_desc)
    return results


def find_similar_players(players: list[dict[str, Any]], seed_id: int, top_n: int = 8) -> list[dict[str, Any]]:
    """Compute standardized cosine similarity over FM attributes & key per-90 rates."""
    seed = next((p for p in players if int(p["player_id"]) == int(seed_id)), None)
    if not seed:
        return []
    is_gk = seed.get("position") == "Goalkeeper"
    feat_attrs = AGROUPS["goalkeeping"] if is_gk else AGROUPS["all"]
    feat_stats = ["saves_per90", "passes_accuracy_avg", "long_balls_per90"] if is_gk else [
        "goals_per90", "assists_per90", "xg_total_per90", "passes_key_per90",
        "dribbles_success_per90", "tackles_total_per90", "interceptions_per90",
        "duels_won_per90", "aerials_won_per90", "touches_per90",
    ]

    cohort = [p for p in players if (p.get("position") == "Goalkeeper") == is_gk]
    if len(cohort) < 2:
        return []

    def _vec(p: dict[str, Any]) -> np.ndarray:
        attrs = p.get("attributes") or {}
        vals = [float(attrs.get(k, 10)) for k in feat_attrs] + [float(p.get(k) or 0.0) for k in feat_stats]
        return np.array(vals, dtype=float)

    mat = np.vstack([_vec(p) for p in cohort])
    means = mat.mean(axis=0)
    stds = np.where(mat.std(axis=0) > 1e-6, mat.std(axis=0), 1.0)
    norm = (mat - means) / stds

    seed_idx = next((i for i, p in enumerate(cohort) if int(p["player_id"]) == int(seed_id)), 0)
    sv = norm[seed_idx]
    sv_n = np.linalg.norm(sv) or 1.0

    scored = []
    for i, p in enumerate(cohort):
        if int(p["player_id"]) == int(seed_id):
            continue
        v = norm[i]
        cos = float(np.dot(sv, v) / (sv_n * (np.linalg.norm(v) or 1.0)))
        sim_pct = max(0, min(99, round(50 + cos * 50)))
        scored.append({"player": p, "similarity": sim_pct})
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_n]


# ---- Team Builder v2 helpers (team_builder_v2.js) ----

def xy_for_field(field: str, all_fields: list[str]) -> tuple[float, float, float]:
    """Port of team_builder_v2.js:174-179 xy(field) calculation."""
    rows = [int(f.split(":")[0]) for f in all_fields]
    max_row = max(rows) if rows else 4
    r, c = (int(x) for x in field.split(":"))
    count = sum(1 for x in rows if x == r)
    cw = 100.0 / (count + 1)
    x = c / (count + 1) * 100.0
    if max_row >= 5:
        y = 90.0 - (r - 1) / max(1, max_row - 1) * 80.0
    else:
        y = 86.0 - (r - 1) / max(1, max_row - 1) * 72.0
    return x, y, cw


def _months_until(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        target = datetime.strptime(date_str[:10], "%Y-%m-%d")
        now = datetime(2026, 11, 19)
        return (target.year - now.year) * 12 + (target.month - now.month)
    except ValueError:
        return None


def evaluate_slot_level(
    starter: dict[str, Any] | None,
    cover: dict[str, Any] | None,
    is_swapped: bool,
    server_slot: dict[str, Any] | None,
    season: str = "now",
) -> dict[str, Any]:
    """Port of team_builder_v2.js:107-118 levelOf(f)."""
    if is_swapped:
        if not starter:
            return {"level": 0, "why": "No one here"}
        short = starter.get("short") or starter.get("name", "Player").split()[-1]
        age = starter.get("age") or 0
        if age >= 30:
            return {"level": 1, "why": f"{short} is {age}"}
        m_left = _months_until(starter.get("contract_until") or starter.get("contract"))
        if m_left is not None and m_left <= 12:
            return {"level": 1, "why": f"{short}'s deal ends {str(starter.get('contract_until'))[:7]}"}
        if cover:
            return {"level": 2, "why": "Covered"}
        return {"level": 0, "why": f"No cover behind {short}"}
    if not server_slot:
        return {"level": 2, "why": "Covered"}
    block = server_slot.get("next" if season == "next" else "now") or {}
    return {"level": int(block.get("level", 2)), "why": block.get("why", "")}


def get_unlocked_fits(club_id: str, position: str, xi_ids: set[int], max_rows: int = 6) -> list[dict[str, Any]]:
    """Return full unlocked recruitment fit candidates for any position."""
    clubs = load_team_builder_clubs()
    players = load_players()
    club = clubs.get(str(club_id), {})
    cached_fits = (club.get("fits") or {}).get(position, {}).get("rows", [])

    rows: list[dict[str, Any]] = []
    seen = set(xi_ids)
    for r in cached_fits:
        pid = int(r["player_id"])
        if pid not in seen:
            seen.add(pid)
            rows.append(r)

    # Supplement with ranked players from players.json matching line/position
    pos_low = position.lower()
    want_group = (
        "Goalkeeper" if "keeper" in pos_low
        else "Defender" if "back" in pos_low
        else "Midfielder" if "midfield" in pos_low
        else "Attacker"
    )
    cands = [
        p for p in players
        if int(p["player_id"]) not in seen
        and (p.get("position") == want_group or (p.get("detailed_position") or "").lower() == pos_low)
    ]
    cands.sort(key=lambda x: float(x.get("rating_avg") or 0), reverse=True)
    for p in cands[: max(0, max_rows - len(rows))]:
        mv = float(p.get("estimated_value_eur") or 12_000_000)
        fit_score = min(96, max(62, round((float(p.get("rating_avg") or 6.9) - 5.8) * 38)))
        rows.append({
            "player_id": int(p["player_id"]),
            "name": p["player_name"],
            "short": p["player_name"].split()[-1],
            "club": p.get("team_name", ""),
            "age": p.get("age"),
            "contract_until": p.get("contract_end") or "2029-06-30",
            "value": format_stat(mv, "eur"),
            "fit": fit_score,
            "star_rating": round(min(5.0, max(3.0, (float(p.get("rating_avg") or 7.0) - 6.0) * 2.5)), 1),
            "tier": "gold",
            "image": p.get("image_path", ""),
            "position": p.get("detailed_position") or position,
        })
    return rows[:max_rows]


# ---- Session-state persistence helpers ----

def init_app_state() -> None:
    """Initialize shared app session state keys cleanly once."""
    if "theme" not in st.session_state:
        st.session_state["theme"] = "light"
    if "pp_recent_players" not in st.session_state:
        st.session_state["pp_recent_players"] = []
    if "watchlists" not in st.session_state:
        st.session_state["watchlists"] = {
            "1": {"id": 1, "name": "Premier League targets", "player_ids": [16827155, 785998, 129602]},
            "2": {"id": 2, "name": "Under-23s across Europe", "player_ids": [37596384, 37559109, 37570379]},
        }
    if "assignments" not in st.session_state:
        st.session_state["assignments"] = {
            "1": {"id": 1, "name": "Under-23 Right-Sided Creator", "deadline": "2026-12-01", "stages": {37596384: "recommended", 16827155: "assessed"}},
            "2": {"id": 2, "name": "Premier League Back-Up GK", "deadline": "2026-11-26", "stages": {37257596: "watching", 432881: "identified"}},
        }
    if "player_notes" not in st.session_state:
        st.session_state["player_notes"] = {
            37596384: "Two-footed receiving in half-spaces, elite progressive carries and 8.99 display vs Costa Rica.",
            16827155: "Consistent 1v1 isolation threat on right touchline; high defensive workrate on counters.",
        }


def record_recent_player(p: dict[str, Any]) -> None:
    rec = [x for x in st.session_state.get("pp_recent_players", []) if int(x["player_id"]) != int(p["player_id"])]
    rec.insert(0, {
        "player_id": int(p["player_id"]),
        "name": p.get("player_name") or p.get("name", "Player"),
        "team": p.get("team_name") or p.get("club", ""),
    })
    st.session_state["pp_recent_players"] = rec[:12]


def toggle_watchlist(wl_id: str, player_id: int) -> bool:
    wl = st.session_state["watchlists"].get(str(wl_id))
    if not wl:
        return False
    pids = wl["player_ids"]
    if player_id in pids:
        pids.remove(player_id)
        return False
    pids.append(player_id)
    return True
