# WIRING_STATUS.md — RealtyDog

What is actually connected end-to-end. A feature is "done" only when its full chain is
unbroken and listed here. **Trace the real call chain — never update from memory.**

Format: `Trigger → Handler → … → Side effect`.

---

## Wired ✅

- **Health check** — `GET /health` → `app.main:health` → `app.db:db_ok()` ping →
  JSON `{status, env, db, jobs}`. Live.
- **Scheduler bootstrap** — app startup (`lifespan`) → `register_jobs()` → APScheduler
  starts **7 jobs**. Live — but every job body is a `log.info("not implemented")` stub.
- **Schema** — `alembic upgrade head` → `0001_initial_schema` → 8 tables
  (`users, sources, parcels, distress_signals, prospects, deals, outreach_log, votes`)
  + `postgis` / `pg_trgm` extensions. **Applied live to Supabase 2026-08-02.**
- **JOB-002 — Tarrant CAD ingest — LIVE (first run 2026-08-02).** Chain:
  `job_cad_refresh` → `fetch_tarrant_parcels` (TAD ArcGIS) → `normalize` (+ church
  classify) → `upsert_parcels` (Supabase PostGIS). **First run: 13,218 Tarrant parcels
  ≥5 acres ingested; 356 church candidates (`meets_buy_box=true`).** The first real
  end-to-end wire. Triggered by `python -m app.ingest.cad_refresh`.

## Partially built 🟡

- **JOB-002b (TAD appraisal-roll join)** — layout CONFIRMED (fixed-length); parser + SPTB
  mapping + `enrich_from_roll` built and wired into `cad_refresh` (`cad_tarrant_roll.py`,
  22 tests). **Dormant only until the roll file is provided:** `load_tarrant_roll()` returns
  `{}` until `TARRANT_ROLL_PATH` points at a downloaded PropertyData FullSet. Once set,
  commercial/industrial/farm classify via `State_Use_Code`. The 15,000 SF check stays
  deferred — the roll has no commercial SF (confirmed).
- **Dallas (DCAD)** — adapter is a gated scaffold (`FIELD_MAP_CONFIRMED=False`); skipped at
  runtime until its field map is confirmed. Primary counties: Dallas + Tarrant.
- **SEL-002 (motivation score)** — built + wired into the nightly job; **run live** (337
  prospects scored). Ranks on owner attributes now; distress weights activate as those
  signals land. `python -m app.score.motivation` to re-run.
- **JOB-001 (tax-sale)** — built + wired + **run live 2026-08-02: 0 parcel matches** (near-zero
  base rate — tax sales are almost all small residential, not 5+ acre parcels). Not a bug; the
  church universe simply has no tax-sale overlap right now. Machinery is correct and will catch
  matches as the universe broadens (commercial). `python -m app.ingest.cad_tax_sale` to re-run.

## NOT wired yet 🔴 (see STUBS.md)

- **All 7 scheduler jobs are stubs** — no data is ingested, scored, or dispatched.
- **No data sources connected** — CAD, tax-sale, foreclosure, probate, 990, Craigslist.
- **No selection** — buy box (SEL-001), motivation score (SEL-002), return gate (SEL-003).
- **No enrichment** (ENR-001), **no dedup** (DEDUP-001).
- **No Telegram bot handlers** (BOT-001) — the UI does not exist yet.
- **No notifications / digest / pipeline / outreach** (NOTIF-001, DIGEST-001, OUTREACH-001).
- **No object storage** wired for photos.

## Deployment

- **Not deployed.** Requires Supabase Postgres+PostGIS, Railway app, env vars, and the
  Telegram bot (INFRA-001 / INFRA-002).

---

*First end-to-end chain to complete: JOB-001 (tax-sale lists) or JOB-002 (CAD universe)
→ SEL-001 (buy box) → SEL-002 (motivation) → DIGEST-001 → NOTIF-001 → Telegram group.
That is the minimum wire that produces a real, notified lead.*
