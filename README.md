# scoutingstats.ai — Free Community Streamlit Clone

A paywall-free, pure-Python recreation of `https://scoutingstats.ai/` designed to run on **Streamlit Community Cloud** for \$0.

## Features Included

1. **Home & Interactive LED Reel (`views/home.py`)**: HTML5 2048x288 animated canvas banner ported from `/static/js/tactics/led_scenes.js`, plus KPI overview.
2. **Global Search Dialog (`services/theme.py`)**: Instant cross-entity search across players, clubs, and 113 unlocked competitions, recent player tracking, and prefix-first ranking (`rank <= 1`).
3. **Scout Hub Player Search (`views/scout_search.py`)**:
   - **Stats vs FM 1–20 Attributes** toggle
   - **8 Lenses** (`Overview`, `Attacking`, `Passing`, `Defending`, `Physical`, `Discipline`, `Context`, `Goalkeeping`)
   - Client-side **Totals vs Per-90** projection across 41 paired metrics
   - Percentile threshold (`Top %`), height, age, market value, foot, contract-end filters, and CSV export
   - **HubPlayerPanel** with relative search-leader bars, last-5 form ratings, Cosine Similarity engine, Head-to-Head Compare, Watchlist toggle, and Notes
4. **Team Builder v2 (`views/team_builder.py`)**:
   - Interactive 2D tactical pitch (`xy_for_field`) with `Thin` / `Watch` / `Covered` depth badges
   - **Today** vs **Next Summer** projection & user swap simulator with Undo/Reset
   - Unlocked **Recruitment Fits** and downloadable **2x Shareable Lineup PNG** (`Pillow`)
5. **Live Fixtures v7 (`views/fixtures.py`)**:
   - Competition/status/search filters, `@st.fragment(run_every="30s")` auto-polling hook, 3-way win probability bar, xG & scoreline model outlook, and SVG minute-by-minute Pressure/Momentum chart
6. **FPL Hub v2 (`views/fpl_hub.py`)**:
   - Real keyless integration with `https://fantasy.premierleague.com/api/` (live squad grade, captaincy, best transfer gain, rank progression SVG sparkline, unlocked Chip Windows, and mini-league standings), plus an instant Demo Squad fallback
7. **Scout Desk v2 (`views/scout_desk.py`)**:
   - Watch schedule board, U22 breakout candidates (`Players to check`), scouting assignment pipeline (`identified -> watching -> assessed -> recommended`), injury flags, and portable JSON workspace backup

---

## Free Accounts / Optional API Keys Needed

| Service | Required? | Cost | When You Need It |
| :--- | :--- | :--- | :--- |
| **GitHub Account** (`https://github.com`) | **Yes** | Free | Required so Streamlit Community Cloud can pull and deploy this folder as a repository. |
| **Streamlit Community Cloud** (`https://share.streamlit.io/`) | **Yes** | Free | Required to host and publish the live web URL (connects directly to your GitHub repo). |
| **Official FPL API** (`fantasy.premierleague.com`) | **No signup** | Free | Keyless and enabled automatically in `services/fpl_client.py`. |
| **Football-Data.org** (`https://www.football-data.org/client/register`) | Optional | Free tier (10 req/min) | Sign up only if you want **live real-world match scores** beyond the bundled matchday seed. Set `FOOTBALL_DATA_API_KEY` in Streamlit Secrets. |
| **Supabase** (`https://supabase.com`) | Optional | Free tier | Sign up only if you want multi-device cloud persistence for Watchlists/Notes across container restarts (the app works out-of-the-box with session storage + JSON export). |

---

## Deploy Free to Streamlit Community Cloud

1. Push the contents of `scoutingstats-streamlit/` to a new GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io/), sign in with GitHub, and click **Create app**.
3. Select your repository, branch (`main`), and set **Main file path** to `app.py`.
4. *(Optional)* Open **Advanced settings -> Secrets** and paste your `FOOTBALL_DATA_API_KEY` from `.streamlit/secrets.toml.example`.
5. Click **Deploy**!

## Local Run (Requires Python 3.10+)

```bash
pip install -r requirements.txt
streamlit run app.py
```
