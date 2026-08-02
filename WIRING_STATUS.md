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
  + `postgis` / `pg_trgm` extensions. Applies cleanly against a PostGIS DB.

## Partially built 🟡

- **JOB-002 (CAD parcel universe)** — code chain complete and unit-tested (10 tests):
  `job_cad_refresh` → `run_cad_refresh` → `fetch_tarrant_parcels` (TAD ArcGIS, verified
  fields) → `normalize` → `upsert_parcels` (PostGIS `parcels`). Dallas adapter is a gated
  scaffold. **Not yet a live wire:** no run against a provisioned PostGIS DB, and
  `meets_buy_box` returns False for every parcel until TAD land-use → `property_type`
  classification lands (SPIKE-000 residual). So the chain *ingests* parcels but produces
  *zero buy-box candidates* yet — by design, fail-closed. Primary counties: Dallas + Tarrant.

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
