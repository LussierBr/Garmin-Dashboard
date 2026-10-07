# Garmin Health Dashboard

A personal web dashboard for your Garmin Connect data, built with Streamlit. Three tabs:

1. **Dashboard**: 30-day vs previous-30-day KPIs, auto-written insights (steps vs that night's sleep, stress vs sleep, weekly rhythm, resting HR trend, 10k streaks), trend charts with 7-day averages, sleep stages, weekday patterns, a correlation map, and notable days.
2. **Ask your data**: type a question like *"does stress affect how long I sleep?"* and get a chart plus a short explanation. Claude picks the two metrics and chart type, pandas computes the numbers, then Claude explains them using only those numbers.
3. **Sleep predictor**: enter a step count and get a predicted sleep score for that night, with an 80% range and an honest accuracy check on your most recent nights.

It ships with synthetic sample data, so it runs before you connect anything.

## Run it

```bash
git clone https://github.com/LussierBr/Garmin-Dashboard.git && cd Garmin-Dashboard
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501. The caption under the title says whether you're looking at **sample data** or **Garmin Connect** data.

## Load your real Garmin data

Set your credentials as environment variables **in your own terminal**. Don't put them in any file in this folder.

```bash
export GARMIN_EMAIL="you@example.com"
export GARMIN_PASSWORD="..."          # Windows PowerShell: $env:GARMIN_PASSWORD="..."
python fetch_garmin.py --days 365
```

- If your account uses two-factor, you'll be asked for the code once.
- After the first login, a session token is saved to `~/.garminconnect`, so later runs don't need the password. You can `unset GARMIN_PASSWORD` afterwards.
- Raw responses are cached per day in `data/raw/`; re-running only downloads new days (plus the last two, which can change). Add `--refresh` to re-download everything.
- The flattened table goes to `data/garmin_daily.csv`. The app uses it automatically instead of the sample data (restart the app or wait up to 10 minutes for its cache).

`data/raw/`, `data/garmin_daily.csv` and `.env` are in `.gitignore` so your health data stays out of any repo.

## Turn on Claude for the Ask tab

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
streamlit run app.py
```

It uses `claude-opus-5-5` by default; set `CLAUDE_MODEL` to use another. Each question makes two small API calls (plan the chart, then explain it). The request opts into server-side refusal fallbacks, so if a safety classifier declines, the API retries on another model automatically. Without a key the tab still works, using keyword matching and a templated explanation.

## How the data lines up

Garmin dates sleep by the morning you wake up. So in the table, `sleep_score` on Tuesday is **Monday night's** sleep. The app adds `tonight_sleep_score` / `tonight_sleep_hours`, which shift sleep back one day so Tuesday's steps and stress sit next to **Tuesday night's** sleep. The predictor and the "that night" insights use these.

## The prediction model

Ordinary least squares on `sleep score that night ~ steps + steps²` (the squared term lets "more steps help, up to a point" show up). You can optionally add today's stress and last night's sleep score. The 80% range is a prediction interval for a single night, not just the uncertainty of the average. "Typical error on recent nights" trains on your earlier 80% of days and scores the most recent 20%, compared against simply guessing your average. Expect steps alone to explain a modest share of sleep variation; the page says so when it does.

## Files

| Path | What it is |
|---|---|
| `app.py` | The Streamlit app (three tabs) |
| `fetch_garmin.py` | Downloads and caches Garmin Connect data |
| `make_sample_data.py` | Writes `data/sample_daily.csv` (synthetic) |
| `garmin_dash/data.py` | Loading, metric catalog, day alignment |
| `garmin_dash/analytics.py` | Insights, notable days, streaks, pair statistics |
| `garmin_dash/charts.py` | Plotly chart builders |
| `garmin_dash/ask.py` | Question → chart plan → stats → explanation |
| `garmin_dash/predict.py` | Sleep-score regression with prediction intervals |
