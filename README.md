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
- The flattened table goes to `data/garmin_daily.csv`. The app uses it automatically instead of the sample data, unless `MONGODB_URI` is set, in which case it reads MongoDB (restart the app or wait up to 10 minutes for its cache).

`data/raw/`, `data/garmin_daily.csv` and `.env` are in `.gitignore` so your health data stays out of any repo.

## Turn on Claude for the Ask tab

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
streamlit run app.py
```

It uses `claude-opus-5-5` by default; set `CLAUDE_MODEL` to use another. Each question makes two small API calls (plan the chart, then explain it). The request opts into server-side refusal fallbacks, so if a safety classifier declines, the API retries on another model automatically. Without a key the tab still works, using keyword matching and a templated explanation.

## Deploy it so others can view it

The deployed setup has three parts. **MongoDB Atlas** holds the data. A **GitHub Action** refreshes it from Garmin every morning. **Streamlit Community Cloud** hosts the app, which reads from MongoDB. Nobody who views it has to run anything.

```
Garmin Connect --(daily GitHub Action: fetch_garmin.py --mongo)--> MongoDB Atlas --(read-only)--> Streamlit app
```

> **Privacy:** this is your health data. Anyone with the app link can see it unless you set `APP_PASSWORD` (step 4), so set one. Anyone who can open the app can also use the Ask tab, which spends your Anthropic credits. This repo is public, but it only contains code and synthetic sample data. The Action's logs print only day counts, never health values or credentials.

### 1. Create the MongoDB cluster (once)

1. Sign up at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) and create a free **M0** cluster.
2. **Database Access** → add two users, each with **Specific Privileges**:
   - `garmin-sync`: `readWrite` on database `garmin` and `readWrite` on database `garmin_auth`. The GitHub Action uses this one.
   - `dashboard-reader`: `read` on database `garmin` only. The website uses this one. It can't see your Garmin session, which is stored in `garmin_auth`.
3. **Network Access** → allow `0.0.0.0/0`. GitHub Actions and Streamlit Cloud don't have fixed IP addresses, so the passwords on those two users are what protect the database.
4. **Connect → Drivers** gives you a connection string for each user, like `mongodb+srv://garmin-sync:<password>@cluster0.xxxxx.mongodb.net/`.

### 2. Backfill your history and save the Garmin session (once, on your computer)

```bash
export GARMIN_EMAIL="you@example.com" GARMIN_PASSWORD="..."
export MONGODB_URI="<garmin-sync connection string>"
python fetch_garmin.py --days 365 --mongo
```

This uploads a year of days. It also stores your Garmin login session in MongoDB, so the daily Action never needs your Garmin password or an MFA code. Each run refreshes the session.

### 3. Turn on the daily sync (GitHub Action)

The workflow is in `.github/workflows/sync-garmin.yml`. It runs at 11:00 UTC every day and re-fetches the last 3 days.

1. Merge this code into `main`. Scheduled workflows only run from the default branch.
2. In the repo, go to **Settings → Secrets and variables → Actions → New repository secret**. Add `MONGODB_URI` with the **garmin-sync** connection string.
3. Under **Actions → Sync Garmin data to MongoDB → Run workflow**, run it once to check that it works.

If a run fails with "saved session has probably expired", repeat step 2 on your computer. GitHub also pauses scheduled workflows in public repos after 60 days with no commits; re-enable it from the Actions tab if that happens.

### 4. Host the app (Streamlit Community Cloud)

1. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub, and choose **Create app**. Pick repo `LussierBr/Garmin-Dashboard`, branch `main`, main file `app.py`.
2. Under **Advanced settings**, choose Python 3.12. Paste your secrets, using `.streamlit/secrets.toml.example` as the template:
   ```toml
   MONGODB_URI = "<dashboard-reader connection string>"
   APP_PASSWORD = "<a password you give to viewers>"
   ANTHROPIC_API_KEY = "sk-ant-..."   # optional, for the Ask tab
   ```
3. Deploy, then share the URL and the password. The app re-reads MongoDB every 10 minutes.

To limit access to specific Google accounts instead of a shared password, set the app to **private** in Streamlit's sharing settings and invite viewers by email. The free tier allows one private app.

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
| `garmin_dash/store.py` | MongoDB read/write for days and the Garmin session |
| `.github/workflows/sync-garmin.yml` | Daily Garmin → MongoDB sync |
| `.streamlit/secrets.toml.example` | Template for the hosted app's secrets |
