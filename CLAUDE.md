# CLAUDE.md — RealtyDog

Guidance for Claude Code (and humans) working in this repo.

## What this is

RealtyDog is an **off-market-first property finder** for a 6-person pooled-investment
group hunting **event-venue (wedding/event) conversion candidates** across the DFW
counties. The full product + architecture spec is **`README.md`** — read it.

---

## Session protocol

**Read `SESSION_PROTOCOL.md` before touching code.** It exists because session
summaries turn *intent* into *completion* — the code and these files are the truth.

### Mandatory reads at session start

```
README.md            ← the build spec (product, selection criteria, schema, roadmap)
STUBS.md             ← open backlog + every stub (the single backlog record)
WIRING_STATUS.md     ← what is actually wired end-to-end
app/main.py          ← what actually starts (FastAPI + APScheduler jobs)
```

### Sanity check

`.claude/hooks/session_start.sh` runs at session start in bash/cloud sessions
(deps → ruff → tests/py_compile). Always exits 0 — surfaces problems, never blocks.
Run manually anytime: `bash .claude/hooks/session_start.sh`.

### "Done" means the wire is traced

A feature is done only when the chain is unbroken and recorded in `WIRING_STATUS.md`:

```
Trigger (scheduler / Telegram) → Handler → data source / enrichment → DB → side effect (alert / pipeline)
```

Never mark done from memory — trace the real call chain.

---

## Architecture

One process (**FastAPI + APScheduler**), one **Postgres (PostGIS + pg_trgm)**,
**Telegram-first**, object storage for photos. Deploy on **Railway + Supabase**
(see README §3, §14).

**Selection is three layers** (README §2):
1. **Buy box** — hard pass/fail filter on parcels.
2. **Motivation score** — off-market ranker (incl. non-profit distress); Hot ≥60 / Warm 30–59 / Cold <30.
3. **Financial return gate** — the pro-forma *is* selection: Year-2 break-even **and** Year-3 EBITDA ≥ 10% within the $5M all-in, at the README §13 assumptions.

**Notification:** Instant (Hot, or new on-market clearing the return gate) / Nightly digest / On-demand. Cold is selected but never notified.

**Data comes only from legal public sources** — CAD, tax-sale lists, courthouse,
ProPublica 990, Craigslist RSS — plus human `/tip` forwards. **NEVER scrape**
MLS / LoopNet / Crexi / Zillow / Facebook.

---

## Commands

```bash
pip install -r requirements.txt
alembic upgrade head          # apply schema (needs a PostGIS DB)
uvicorn app.main:app --reload # run locally (http://localhost:8000/health)
ruff check .
pytest -q
```

---

## Key files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI + APScheduler bootstrap, `/health`, job registration |
| `app/config.py` | Env settings (buy box, thresholds, API keys) |
| `app/db.py` | SQLAlchemy engine/session + health ping |
| `alembic/versions/0001_initial_schema.py` | Full schema (README §7) |
| `Dockerfile` / `railway.toml` | Deploy |
| `README.md` | The build spec |
| `STUBS.md` / `WIRING_STATUS.md` | Backlog / wiring status |

---

## Conventions

- **Missing data ≠ a green light.** A source returning nothing means "unverified,"
  not "passes." Buy-box and financial gates **fail closed** on missing data;
  discovery-only reads **fail open**.
- **Mail-first outreach.** Direct mail via the CAD mailing address ($0 skip-trace);
  only pay per-hit to skip-trace a hot lead you'll *call*. Respect TCPA / DNC / CAN-SPAM.
- **Scoring is an explainable rubric, not a black-box score.** Always store `score_breakdown`.
- **Zoning is a research checklist, not an automated verdict** (liability line).
- **Every stub → `STUBS.md` in the same change, with the *reasoning*** (why, what it
  builds on, what gate it must clear) — not just what it does.
- **Schema change** updates the migration AND any ORM/dataclass in the same commit.
- **Repo stays PRIVATE** (confidential fund strategy). Commit as
  `aiagent007700 <aiagent007700@gmail.com>`; push with the Bash sandbox disabled (network).

## Buy box (current)

DFW + ring counties · ≥5 acres · ≥15,000 SF existing structure · ≤$4M purchase ·
**≤$5M all-in (binding)** · barn/church/commercial retrofit · 300+ capacity ·
≤6-month go-live. Motivation buckets: Hot ≥60 / Warm 30–59 / Cold <30.
