# Open WebUI Usage Widget

A lightweight, self-contained **token/usage widget for [Open WebUI](https://github.com/open-webui/open-webui)**.
Shows a small pill in the bottom-right corner of the UI with your token usage;
click it to open a panel with totals, a 24-hour sparkline, and per-model breakdown.

**No Open WebUI code changes. No rebuild.** Just two static files and a tiny
collector script.

```
┌──────────────────────────────┐
│  ● 95.65M · 2.1K req         │   ← pill (always visible)
└──────────────────────────────┘
   click ↓
┌────────────────────────────┐
│ Open WebUI Usage        ×  │
│ 95.65M  tokens tracked     │
│ ┌ PROMPT ┐  ┌ COMPLETION ┐ │
│ │ 94.47M │  │   1.17M    │ │
│ └────────┘  └────────────┘ │
│ LAST 24 HOURS   ▁▂▃▅▇▅▃▂▁  │
│ TOP MODELS  ...            │
└────────────────────────────┘
```

## How it works

1. **`loader.js`** — Open WebUI already loads `/static/loader.js` on every page
   (`<script src="/static/loader.js" defer>` in `index.html`). We bind-mount our
   own `loader.js` over it. It injects a small iframe with the widget.
2. **`usage-widget.html`** — the widget UI, served from `/static/usage/`. The
   iframe is pill-sized with `pointer-events: auto` (fully interactive) and
   reports its needed size to the parent via `postMessage`, so it never covers
   more of the app than the widget actually uses.
3. **`usage-collector.py`** — reads your request log (JSONL) and writes
   `usage-stats.json` next to the widget. Run it from cron or a systemd timer
   every minute. The widget fetches it and auto-refreshes every 60s.

The iframe is **not** full-viewport and never blocks the app: it's sized
exactly to the pill/panel via postMessage negotiation.

## Install (docker compose)

```yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    volumes:
      - open-webui:/app/backend/data
      # 1. widget loader (replaces the stock no-op loader.js)
      - ./widget/loader.js:/app/build/static/loader.js:ro
      # 2. widget UI + stats JSON
      - ./widget:/app/backend/open_webui/static/usage:ro
      # 3. live stats written by the collector
      - ./stats:/app/backend/open_webui/static/usage/stats
    ...
```

> **Important:** mount the stats JSON directory read-write for the collector
> (or `docker cp` the file in from a timer — see below). The widget HTML and
> loader can stay read-only.

### Collector

```bash
# .env or crontab
USAGE_LOG_JSONL=/path/to/requests.jsonl
USAGE_TOTALS=/path/to/totals.json      # optional pre-aggregated totals
USAGE_OUT=/path/to/usage-stats.json    # must land in the mounted stats dir
USAGE_BUDGET=0                         # weekly token budget, 0 = tracking only

# every minute via cron:
* * * * * python3 /path/to/usage-collector.py
```

Or with a systemd user timer — see [`examples/`](examples/).

If you can't mount a writable dir into the container, have the collector write
to the host and `docker cp` the file in (that's what `examples/push-stats.sh`
does).

## Stats format

`usage-stats.json`:

```json
{
  "generated": 1758000000,
  "since": 1757000000,
  "budget": 0,
  "totals": {"total": 95650000, "prompt": 94470000, "completion": 1170000,
             "cached": 81520000, "requests": 2100},
  "recent": {"total": 69840000, "requests": 1500},
  "hourly": [{"h": "01:00", "t": 120000}],
  "models": [{"name": "gpt-4o", "total": 24060000, "requests": 551,
              "route": "VISION"}]
}
```

`route` is optional — if present it's shown as a coloured tag next to the
model name. Known tags: `FAST`, `RIDER`, `CODE`, `PLAN`, `DOCS`, `HARD`,
`VISION` (unknown tags render unstyled).

## Adapting to your data source

The collector only needs a JSONL file with `ts` and `total` per request. Any
proxy that logs requests can feed it — e.g. a LiteLLM proxy, a custom
middleware, or Open WebUI's own request logs if you export them. See
[`collector/usage-collector.py`](collector/usage-collector.py) for the exact
fields.

## Files

```
widget/loader.js           injected into Open WebUI (bind-mount over stock loader)
widget/usage-widget.html   the widget UI (pill + panel)
collector/usage-collector.py  JSONL → usage-stats.json
examples/                  systemd units + docker cp push script
```

## License

MIT
