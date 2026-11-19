"""Home Landing View — LED Hoarding Canvas Reel (ported from led_scenes.js) & Feature Hub."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from services.data_store import load_leagues, load_players, load_team_builder_clubs
from services.fixtures_client import load_fixtures_seed

LED_BANNER_HTML = """
<div style="border-radius:14px;overflow:hidden;border:1px solid rgba(255,255,255,0.12);background:#0d1b2e;">
  <canvas id="ledBanner" width="2048" height="288" style="width:100%;height:auto;display:block;"></canvas>
</div>
<script>
(() => {
  const LED_W = 2048, LED_H = 288, SPOT_MS = 4200, WIPE_MS = 900;
  const BG = '#0d1b2e', ACCENT = '#f97316';
  const FONT = 'Inter, system-ui, -apple-system, sans-serif';
  const spots = [
    { kind: 'tagline', line: 'SCOUTINGSTATS COMMUNITY EDITION', palette: { dark:'#0E1A4A', mid:'#1B3689', light:'#2F6AE0', accent:'#5B8CFF' } },
    { kind: 'tagline', line: '113+ UNLOCKED LEAGUES · PER-90 & FM 1-20', palette: { dark:'#160b03', mid:'#5c2e0a', light:'#E8652E', accent:'#F5C451' } },
    { kind: 'strip', items: ['PLAYER SEARCH', 'TEAM BUILDER V2', 'LIVE FIXTURES', 'FPL HUB V2'], palette: { dark:'#04160c', mid:'#14532d', light:'#3FB57A', accent:'#7EE2A8' } }
  ];
  const canvas = document.getElementById('ledBanner');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

  function paintSpot(c, spot, age) {
    const p = spot.palette;
    const g = c.createLinearGradient(0, 0, LED_W, LED_H);
    g.addColorStop(0, p.dark); g.addColorStop(0.42, p.mid); g.addColorStop(0.72, p.light); g.addColorStop(1, p.dark);
    c.fillStyle = g; c.fillRect(0, 0, LED_W, LED_H);
    const scrim = c.createLinearGradient(0, 0, LED_W, 0);
    scrim.addColorStop(0, 'rgba(13,27,46,0)'); scrim.addColorStop(0.28, 'rgba(13,27,46,0.58)');
    scrim.addColorStop(0.72, 'rgba(13,27,46,0.58)'); scrim.addColorStop(1, 'rgba(13,27,46,0)');
    c.fillStyle = scrim; c.fillRect(0, 0, LED_W, LED_H);

    const k = clamp(age / 520, 0, 1);
    const ease = 1 - Math.pow(1 - k, 3);
    c.save();
    c.globalAlpha = ease;
    c.translate(0, (1 - ease) * 24);
    c.textBaseline = 'middle';
    const midY = LED_H / 2 + 4;
    if (spot.kind === 'tagline') {
      c.textAlign = 'center';
      let size = 96, w = 0;
      for (;;) {
        c.font = '800 ' + size + 'px ' + FONT;
        w = c.measureText(spot.line).width;
        if (w <= LED_W * 0.86 || size <= 48) break;
        size -= 6;
      }
      c.fillStyle = '#ffffff';
      c.fillText(spot.line, LED_W / 2, midY - 12);
      const barW = Math.min(w, LED_W * 0.86) * ease;
      c.fillStyle = p.accent;
      c.fillRect(LED_W / 2 - barW / 2, midY + 58, barW, 8);
    } else {
      const items = spot.items, gap = 40, dotR = 8;
      let size = 78;
      c.font = '700 ' + size + 'px ' + FONT;
      const widths = items.map(it => c.measureText(it).width);
      const total = widths.reduce((a, b) => a + b, 0) + (items.length - 1) * gap * 2;
      let x = (LED_W - total) / 2;
      c.textAlign = 'left';
      items.forEach((it, i) => {
        c.fillStyle = '#ffffff'; c.fillText(it, x, midY); x += widths[i];
        if (i < items.length - 1) {
          c.beginPath(); c.arc(x + gap, midY - 4, dotR, 0, Math.PI * 2);
          c.fillStyle = p.accent; c.fill(); x += gap * 2;
        }
      });
    }
    c.restore();
  }

  const t0 = performance.now();
  function frame(now) {
    const t = now - t0, cyc = SPOT_MS + WIPE_MS, n = spots.length;
    const tt = t % (cyc * n), idx = Math.floor(tt / cyc), local = tt - idx * cyc;
    paintSpot(ctx, spots[idx], local);
    if (local > SPOT_MS) {
      const pr = (local - SPOT_MS) / WIPE_MS;
      const e = pr < 0.5 ? 2 * pr * pr : 1 - Math.pow(-2 * pr + 2, 2) / 2;
      const edge = LED_W * e;
      ctx.save(); ctx.beginPath(); ctx.rect(0, 0, edge, LED_H); ctx.clip();
      paintSpot(ctx, spots[(idx + 1) % n], local - SPOT_MS);
      ctx.restore();
      const blade = ctx.createLinearGradient(edge - 96, 0, edge + 8, 0);
      blade.addColorStop(0, ACCENT + '00'); blade.addColorStop(0.72, ACCENT + 'd9'); blade.addColorStop(1, 'rgba(255,255,255,0.95)');
      ctx.fillStyle = blade; ctx.fillRect(edge - 96, 0, 104, LED_H);
    }
    ctx.fillStyle = ACCENT; ctx.fillRect(0, 0, LED_W, 6);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
</script>
"""

components.html(LED_BANNER_HTML, height=130)

players = load_players()
leagues = load_leagues()
clubs = load_team_builder_clubs()
fixtures = load_fixtures_seed().get("competitions", [])
fix_count = sum(len(c.get("rows", [])) for c in fixtures)

st.markdown("## Free Football Intelligence, Reconstructed")
st.markdown(
    "A paywall-free recreation of `scoutingstats.ai` built from its client-side architecture, "
    "featuring all 8 Scout Search lenses, Per-90 projections, FM 1–20 attribute scoring, Team Builder depth & fit discovery, "
    "Poisson Fixtures Inspector, and live keyless Fantasy Premier League sync."
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Players Indexed", f"{len(players):,}", "100% Unlocked")
c2.metric("Unlocked Competitions", f"{len(leagues):,}", "Global Directory")
c3.metric("Team Builder Clubs", f"{len(clubs):,}", "2x PNG Share Cards")
c4.metric("Matchday Fixtures", f"{fix_count:,}", f"{len(fixtures)} Leagues")

st.markdown("---")
st.markdown("### Explore Workspace")

pages = st.session_state.get("_nav_pages", {})
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.markdown(
        '<div class="ss-card"><div class="ss-label">Scout Hub Search</div>'
        '<h4>Advanced Player Database</h4>'
        '<p style="color:var(--ss-text-2);font-size:13.5px;">Switch instantly between 8 stat lenses and Totals vs Per-90, '
        'filter by FM 1–20 attributes, inspect form bars & find similar profiles.</p></div>',
        unsafe_allow_html=True,
    )
    if st.button("Open Player Search →", key="home_go_search", use_container_width=True, type="primary"):
        st.switch_page(pages["search"])

    st.markdown(
        '<div class="ss-card"><div class="ss-label">FPL Hub v2</div>'
        '<h4>Live Gameweek Planner</h4>'
        '<p style="color:var(--ss-text-2);font-size:13.5px;">Connect any Fantasy Premier League ID via the free official API '
        'or load our demo squad for grade percentiles, chip windows, and rank sparklines.</p></div>',
        unsafe_allow_html=True,
    )
    if st.button("Open FPL Hub →", key="home_go_fpl", use_container_width=True):
        st.switch_page(pages["fpl"])

with col_b:
    st.markdown(
        '<div class="ss-card"><div class="ss-label">Team Builder v2</div>'
        '<h4>Squad Depth & Recruitment</h4>'
        '<p style="color:var(--ss-text-2);font-size:13.5px;">Audit XI thin/watch slots now and next summer, swap players live on the pitch, '
        'browse unlocked transfer fits, and download 2x PNG share cards.</p></div>',
        unsafe_allow_html=True,
    )
    if st.button("Open Team Builder →", key="home_go_tb", use_container_width=True):
        st.switch_page(pages["builder"])

    st.markdown(
        '<div class="ss-card"><div class="ss-label">Scout Desk v2</div>'
        '<h4>Watchlists & Assignments</h4>'
        '<p style="color:var(--ss-text-2);font-size:13.5px;">Track upcoming fixtures for your shortlisted players, review U22 breakout ratings, '
        'update scouting pipeline stages, and save match notes.</p></div>',
        unsafe_allow_html=True,
    )
    if st.button("Open Scout Desk →", key="home_go_desk", use_container_width=True):
        st.switch_page(pages["desk"])

with col_c:
    st.markdown(
        '<div class="ss-card"><div class="ss-label">Live Fixtures v7</div>'
        '<h4>Model Odds & Momentum</h4>'
        '<p style="color:var(--ss-text-2);font-size:13.5px;">Filter matches across competitions with win probability bars, '
        'xG outlook, exact score probabilities, SVG pressure graphs, and optional live scores.</p></div>',
        unsafe_allow_html=True,
    )
    if st.button("Open Fixtures →", key="home_go_fix", use_container_width=True):
        st.switch_page(pages["fixtures"])
