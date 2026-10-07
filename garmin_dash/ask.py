"""Natural-language "compare X and Y" questions, Genie style.

Step 1: Claude turns the question into a chart plan (which two metrics, which
chart, what time window), constrained to a JSON schema of the metrics we have.
Step 2: pandas computes the chart and the statistics.
Step 3: Claude writes a short explanation grounded in those computed numbers.

Without ANTHROPIC_API_KEY it falls back to keyword matching and a templated
explanation, so the tab still works offline.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import pandas as pd

from . import charts
from .analytics import pair_stats, strength_word
from .data import METRICS, with_unit

MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
CHART_TYPES = {
    "scatter": "each day as a dot, X vs Y, with a trend line; best for 'does X affect Y'",
    "buckets": "average Y for low/medium/high quarters of X; best for 'when X is high, what happens to Y'",
    "over_time": "both metrics as 7-day averages over time on one indexed axis; best for 'how have X and Y trended'",
    "weekday": "both metrics averaged by day of week; best for weekly rhythm questions",
}


@dataclass
class Answer:
    x: str
    y: str
    chart_type: str
    days: int | None
    title: str
    figure: object
    explanation: str
    stats: dict
    used_claude: bool


def _client():
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    import anthropic
    return anthropic.Anthropic()


def _call_json(client, system: str, user: str, schema: dict, effort: str = "low") -> dict:
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",  # retry on another model if a safety classifier declines
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("Claude declined this question.")
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)


def _plan_with_claude(client, question: str, metric_keys: list[str]) -> dict:
    catalog = "\n".join(f"- {k}: {METRICS[k].label} ({METRICS[k].unit}). {METRICS[k].description}" for k in metric_keys)
    charts_txt = "\n".join(f"- {k}: {v}" for k, v in CHART_TYPES.items())
    schema = {
        "type": "object",
        "properties": {
            "x": {"type": "string", "enum": metric_keys, "description": "the driver / first metric"},
            "y": {"type": "string", "enum": metric_keys, "description": "the outcome / second metric"},
            "chart_type": {"type": "string", "enum": list(CHART_TYPES)},
            "days": {"type": ["integer", "null"], "description": "limit to the last N days, or null for all history"},
            "title": {"type": "string", "description": "short chart title, under 70 characters"},
        },
        "required": ["x", "y", "chart_type", "days", "title"],
        "additionalProperties": False,
    }
    system = (
        "You turn a person's question about their own Garmin health data into a chart plan. "
        "Pick the two metrics from the catalog that best match what they asked, and the chart type that answers it. "
        "Sleep columns named 'last night' describe the night before that day; 'that night' columns describe the night after. "
        "When the question is whether something done during the day affects sleep, use a 'that night' sleep metric as y. "
        "If they name only one metric, pick the most sensible partner. Use null for days unless they mention a time window.\n\n"
        f"Metric catalog:\n{catalog}\n\nChart types:\n{charts_txt}"
    )
    plan = _call_json(client, system, question, schema)
    if plan["x"] == plan["y"]:
        plan["y"] = "tonight_sleep_score" if plan["x"] != "tonight_sleep_score" else "steps"
    return plan


def _explain_with_claude(client, question: str, plan: dict, stats: dict, period: str) -> str:
    schema = {
        "type": "object",
        "properties": {"explanation": {"type": "string"}},
        "required": ["explanation"],
        "additionalProperties": False,
    }
    system = (
        "You explain a chart of someone's own wearable data to them, in plain, friendly language. "
        "Write 3 to 5 sentences of Markdown, addressed to them as 'you'. Lead with the answer to their question. "
        "Use only the numbers provided; round sensibly. Say how strong the relationship is in everyday words, "
        "mention the number of days it rests on, and note that correlation is not causation only when the link looks meaningful. "
        "If the relationship is weak, say so plainly rather than over-reading it. No headings, no bullet lists."
    )
    user = json.dumps({
        "question": question,
        "chart": plan["chart_type"],
        "period": period,
        "x": {"key": plan["x"], "label": METRICS[plan["x"]].label, "unit": METRICS[plan["x"]].unit, "description": METRICS[plan["x"]].description},
        "y": {"key": plan["y"], "label": METRICS[plan["y"]].label, "unit": METRICS[plan["y"]].unit, "description": METRICS[plan["y"]].description},
        "stats": stats,
    }, default=str)
    return _call_json(client, system, user, schema)["explanation"]


# ---- offline fallback -------------------------------------------------------

_KEYWORDS = [
    (r"\bsleep score\b.*\b(tonight|that night|after)\b|\bthat night\b", "tonight_sleep_score"),
    (r"\bsleep (score|quality)\b", "sleep_score"),
    (r"\b(sleep duration|hours of sleep|how long i sleep|sleep length)\b", "sleep_hours"),
    (r"\bdeep\b", "deep_hours"), (r"\brem\b", "rem_hours"), (r"\bbedtime|go to bed\b", "bedtime_hour"),
    (r"\bsleep\b", "tonight_sleep_score"),
    (r"\bresting\b|\brhr\b|\bheart\b", "resting_hr"),
    (r"\bpeak stress|max stress\b", "max_stress"), (r"\bstress\b", "avg_stress"),
    (r"\bsteps?\b|\bwalk", "steps"), (r"\bdistance\b|\bkm\b|\bmiles?\b", "distance_km"),
    (r"\bcalorie|kcal\b", "active_kcal"), (r"\bbody battery\b|\benergy\b", "body_battery_high"),
]


def _plan_offline(question: str, metric_keys: list[str]) -> dict:
    q = question.lower()
    hits: list[tuple[int, str]] = []
    for pat, key in _KEYWORDS:
        m = re.search(pat, q)
        if m and key in metric_keys and key not in [k for _, k in hits]:
            hits.append((m.start(), key))
    found = [k for _, k in sorted(hits)]
    if not found:
        found = ["steps", "tonight_sleep_score"]
    if len(found) == 1:
        found.append("tonight_sleep_score" if "sleep" not in found[0] else "steps")
    x, y = found[0], found[1]
    # Put sleep on the y axis when it's one of the two.
    if "sleep" in x and "sleep" not in y:
        x, y = y, x
    if re.search(r"over time|trend|month|week(s)? |since", q):
        chart = "over_time"
    elif re.search(r"weekday|day of (the )?week|weekend", q):
        chart = "weekday"
    elif re.search(r"\bwhen\b|high|low|more|less|bucket", q):
        chart = "buckets"
    else:
        chart = "scatter"
    m = re.search(r"last (\d+) (day|week|month)", q)
    days = int(m.group(1)) * {"day": 1, "week": 7, "month": 30}[m.group(2)] if m else None
    return {"x": x, "y": y, "chart_type": chart, "days": days,
            "title": f"{METRICS[x].label} vs {METRICS[y].label}"}


def _explain_offline(plan: dict, stats: dict) -> str:
    if stats.get("n", 0) < 5:
        return "There aren't enough days with both metrics recorded to say anything yet."
    x, y = METRICS[plan["x"]], METRICS[plan["y"]]
    r = stats["pearson_r"]
    t = stats["tercile_means"]
    lo, hi = t.get("low"), t.get("high")
    text = (f"Across **{stats['n']} days**, {x.label.lower()} and {y.label.lower()} have a "
            f"**{strength_word(r)} {'positive' if r > 0 else 'negative'}** relationship (r = {r:.2f}).")
    if lo and hi:
        xk, yk = plan["x"], plan["y"]
        text += (f" On the third of days with the lowest {x.label.lower()} ({METRICS[xk].fmt.format(lo['x_range'][0])} to {with_unit(xk, lo['x_range'][1])}), "
                 f"{y.label.lower()} averaged **{with_unit(yk, lo['y_mean'])}**, versus **{with_unit(yk, hi['y_mean'])}** on the highest third "
                 f"({METRICS[xk].fmt.format(hi['x_range'][0])} to {with_unit(xk, hi['x_range'][1])}).")
    text += " _(Offline summary: set ANTHROPIC_API_KEY for Claude-written explanations.)_"
    return text


# ---- entry point ------------------------------------------------------------

def answer(question: str, df: pd.DataFrame, metric_keys: list[str]) -> Answer:
    client = _client()
    plan = None
    if client:
        plan = _plan_with_claude(client, question, metric_keys)
    else:
        plan = _plan_offline(question, metric_keys)

    d = df
    period = "all history"
    if plan.get("days"):
        d = df[df["date"] > df["date"].max() - pd.Timedelta(days=int(plan["days"]))]
        period = f"last {plan['days']} days"
    x, y, title = plan["x"], plan["y"], plan["title"]

    builders = {"scatter": charts.scatter, "buckets": charts.bucket_bars,
                "over_time": charts.over_time_indexed, "weekday": charts.weekday_pair}
    fig = builders[plan["chart_type"]](d, x, y, title=title)

    stats = pair_stats(d, x, y)
    stats["period"] = f"{d['date'].min():%b %d, %Y} to {d['date'].max():%b %d, %Y}"
    if plan["chart_type"] == "weekday":
        stats["weekday_means"] = {
            col: d.groupby("weekday")[col].mean().round(2).dropna().to_dict() for col in (x, y)
        }

    if client:
        explanation = _explain_with_claude(client, question, plan, stats, period)
    else:
        explanation = _explain_offline(plan, stats)
    return Answer(x, y, plan["chart_type"], plan.get("days"), title, fig, explanation, stats, client is not None)
