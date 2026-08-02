# STUBS.md — RealtyDog backlog & stub log

The single source of truth for open work: every stub, TODO, disconnected wire, and
backlog item. **Each entry states the *reasoning*** (why it's needed, what it builds
on, what gate it must clear) — not just what to build. Log a new stub in the same
change that creates it. When an item is fully wired end-to-end, move it to
`WIRING_STATUS.md`.

Status: 🔴 not started · 🟡 in progress · 🟢 done

---

## Phase 0 — setup (do first)

- **SPIKE-000 — Per-county CAD access spike** 🔴
  The whole discovery backbone is CAD parcel data, and every county publishes it
  differently (bulk vs. search-only vs. paid; different fields/formats). Nothing that
  depends on the parcel universe can be built until we know what each primary county
  actually offers. Record findings in a `sources` row per county. README §5 Job 0.
  **Blocks JOB-002, JOB-008.**
- **INFRA-001 — Provision Postgres+PostGIS + deploy** 🔴
  Supabase project (PostGIS preinstalled) + Railway app + env vars → `alembic upgrade head`.
  README §14. Needed before any job can persist data.
- **INFRA-002 — Telegram bot + group** 🔴
  BotFather token + group chat ID + the 6 allowed Telegram IDs (`ALLOWED_TELEGRAM_IDS`).
  The bot is the entire UI; nothing is user-visible until this exists.

## Ingestion jobs (currently `log.info("not implemented")` stubs in `app/main.py`)

- **JOB-001 — Tax-sale list parser** 🔴 (Job 1, P0)
  Highest yield/effort: pre-filtered distressed owners, DFW-wide, free. Parse
  LGBS / MVBA / Perdue Brandon HTML+PDF → `distress_signals(signal_type='tax_sale')`.
  Match by APN/legal description (rows lack clean street addresses). First real leads.
- **JOB-002 — CAD parcel universe** 🔴 (Job 2, P0)
  The universe of buy-box candidates + owner mailing addresses (enables mail-first).
  Bulk CAD for 2–3 primary counties → `parcels`; compute `meets_buy_box` + absentee /
  tenure / owner_type. Depends on SPIKE-000. **Every off-market prospect derives from here.**
- **JOB-003 — Foreclosure postings** 🔴 (Job 3, P1)
  Substitute Trustee notices (county clerk, first-Tuesday sales) → `distress_signals`.
- **JOB-004 — Probate + Lis Pendens** 🔴 (Job 4, P1)
  Estates / litigation pressure. Fuzzy name-match → store `match_confidence`, never
  hard-merge below threshold.
- **JOB-005 — Code violations** 🔴 (Job 5, P2)
  City open-data portals. Deferred until P0/P1 are flowing.
- **JOB-006 — Skip-trace (hot leads)** 🔴 (Job 6, P2)
  On-demand only, pay-per-hit. Mail-first means we don't need it until we choose to
  *call* a hot lead. Not scheduled.
- **JOB-007 — Craigslist RSS** 🔴 (Job 7, P1)
  The one clean auto social feed (per-search RSS). Keyword-filter to buy box →
  `deals(source='social')`. No scraping.
- **JOB-008 — Non-profit 990 distress** 🔴 (Job 8, P1)
  The sharpest off-market lane (spec input #1): cross CAD tax-exempt owners against
  ProPublica 990 financials → `distress_signals(signal_type='nonprofit_distress')` (+35).
  Depends on JOB-002. Churches don't file 990 — use the proxy path (README §8).

## Selection & scoring

- **SEL-001 — Buy-box filter (Layer 1)** 🔴
  Hard pass/fail on parcels (README §2); sets `meets_buy_box`. Missing physical/financial
  data **fails closed**.
- **SEL-002 — Motivation score (Layer 2)** 🔴
  Explainable point-sum over `distress_signals` + owner attributes →
  `prospects.motivation_score` + `score_breakdown` (records *why*). Buckets Hot/Warm/Cold.
- **SEL-003 — Financial return gate (Layer 3)** 🔴
  The pro-forma *is* selection: Year-2 break-even AND Year-3 EBITDA ≥ 10% within the
  $5M all-in, at the README §13 standard assumptions. Populates `deals.all_in_cost /
  breakeven_year / y3_ebitda_pct / meets_return_gate`. Needs ENR-001.
- **ENR-001 — Enrichment** 🔴
  Per property: zoning/jurisdiction research checklist (NOT an automated permitted-use
  verdict — liability), Google Maps proximity (airport/highway/hotels, cache 7d), FEMA
  flood, comparable venues, competitor-utilization estimate. Feeds SEL-003 + the deal card.
- **DEDUP-001 — Cross-source dedup** 🔴
  Same property from multiple feeds: match on `apn` first, then normalized address +
  `pg_trgm` above threshold. Prevents double-counting and double-notifying.

## Bot, notifications, pipeline

- **BOT-001 — Telegram handlers** 🔴
  `/analyze <url|apn>` (the pull-first core), `/prospects`, `/tip`, `/pipeline`, `/vote`,
  mail-merge export. Owner-allowlist gate. README §9.
- **NOTIF-001 — Notification tiers + dedup ledger** 🔴
  Instant (Hot, or new on-market clearing the return gate) / Nightly digest / On-demand.
  Dedup ledger keyed on parcel+signal so nothing double-fires. Cold selected, never notified.
- **DIGEST-001 — Nightly score + digest job** 🔴
  Recompute motivation + return gate → emit new-hot-prospect digest to the group.
- **OUTREACH-001 — Outreach CRM + mail-merge** 🔴
  `prospects` status pipeline (prospect → contacted → responded → analyzing → offer),
  `outreach_log`, CSV export (name + CAD mailing address) for a mail run. Tune motivation
  weights against `outreach_log` responses — the one real feedback signal we get.

---

## Open decisions (block related work)

1. **Primary 2–3 counties** — drives SPIKE-000 / JOB-002.
2. **Who owns the mail send** — `prospects.assigned_to` needs a real person.
3. **Entity + operating agreement** — how a `/vote` records a group decision.
4. **Standard return-gate assumptions** — negotiated-discount %, conversion $/SF, ramp
   curve (README §13). These literally decide what selects.
5. **Validate the competitor-utilization estimate** against 3–5 known DFW venues before
   it is allowed to hard-reject a sub-market.
