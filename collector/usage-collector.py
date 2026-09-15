#!/usr/bin/env python3
"""usage-collector.py — publish usage stats as JSON for the Open WebUI usage widget.

Reads a JSONL log of requests (one JSON object per line) and writes a compact
JSON summary the widget iframe fetches. Run from cron/systemd every minute.

Expected JSONL fields (extra fields are ignored):
    ts        unix timestamp (float)      [required]
    total     total tokens (int)          [required]
    model     model name (str)            [optional]
    route     route/category tag (str)    [optional]
    prompt    prompt tokens (int)         [optional]
    completion completion tokens (int)    [optional]
    cached    cached tokens (int)         [optional]

Output shape:
{
  "generated": <unix ts>,
  "since":     <unix ts of first recorded request>,
  "budget":    <weekly token budget, 0 = none>,
  "totals":    {"total","prompt","completion","cached","requests"},
  "recent":    {"total","requests"},            # last 24h
  "hourly":    [{"h":"HH:00","t":tokens}, ...], # last 24 buckets
  "models":    [{"name","total","requests","route"}, ...]  # top 8
}

Env vars:
    USAGE_LOG_JSONL   path to the JSONL request log   (required)
    USAGE_TOTALS      path to a totals JSON with keys total_tokens,
                      prompt_tokens, completion_tokens, cached_tokens,
                      requests, since   (optional — falls back to scanning JSONL)
    USAGE_OUT         output path                     (default: ./usage-stats.json)
    USAGE_BUDGET      weekly token budget, 0 = none   (default: 0)
"""
import json
import os
import sys
import time
from collections import defaultdict

HOUR = 3600
DAY = 24 * HOUR

LOG_JSONL = os.environ.get("USAGE_LOG_JSONL", "")
TOTALS_FILE = os.environ.get("USAGE_TOTALS", "")
OUT = os.environ.get("USAGE_OUT", "usage-stats.json")
BUDGET = int(os.environ.get("USAGE_BUDGET", "0") or 0)


def main():
    now = time.time()
    totals = {"total": 0, "prompt": 0, "completion": 0, "cached": 0,
              "requests": 0, "since": None}

    # Optional pre-aggregated totals file (fast path for big logs)
    if TOTALS_FILE:
        try:
            with open(TOTALS_FILE) as fh:
                t = json.load(fh)
            totals = {
                "total": int(t.get("total_tokens") or 0),
                "prompt": int(t.get("prompt_tokens") or 0),
                "completion": int(t.get("completion_tokens") or 0),
                "cached": int(t.get("cached_tokens") or 0),
                "requests": int(t.get("requests") or 0),
                "since": t.get("since"),
            }
        except (OSError, ValueError):
            pass

    by_model = defaultdict(lambda: {"total": 0, "requests": 0, "route": None})
    hourly = defaultdict(int)
    recent_total = recent_req = 0
    first_ts = None

    try:
        with open(LOG_JSONL) as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                ts = float(e.get("ts") or 0)
                if not ts:
                    continue
                if first_ts is None or ts < first_ts:
                    first_ts = ts
                total = int(e.get("total") or 0)
                if ts >= now - DAY:
                    recent_total += total
                    recent_req += 1
                    m = by_model[e.get("model") or "unknown"]
                    m["total"] += total
                    m["requests"] += 1
                    if e.get("route"):
                        m["route"] = e["route"]
                    hourly[int(ts // HOUR)] += total
    except OSError:
        pass

    if not totals["since"]:
        totals["since"] = first_ts or now

    out = {
        "generated": int(now),
        "since": int(totals["since"]),
        "budget": BUDGET,
        "totals": {k: totals[k] for k in
                   ("total", "prompt", "completion", "cached", "requests")},
        "recent": {"total": recent_total, "requests": recent_req},
        "hourly": [],
        "models": [],
    }

    start = int(now // HOUR) - 23
    for i in range(24):
        bucket = start + i
        out["hourly"].append({
            "h": time.strftime("%H:00", time.localtime(bucket * HOUR)),
            "t": hourly.get(bucket, 0),
        })

    top = sorted(by_model.items(), key=lambda kv: kv[1]["total"], reverse=True)[:8]
    out["models"] = [
        {"name": name, "total": v["total"], "requests": v["requests"],
         "route": v["route"]}
        for name, v in top
    ]

    tmp = OUT + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(out, fh)
    os.replace(tmp, OUT)
    sys.stderr.write("[usage-collector] wrote %s (%d bytes)\n"
                     % (OUT, os.path.getsize(OUT)))


if __name__ == "__main__":
    main()
