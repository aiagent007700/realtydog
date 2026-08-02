# RealtyDog — Build Spec

**The off-market deal scout for our event-venue fund.** Finds retrofittable barn / church / commercial buildings on 5+ acres across the DFW counties that can seat 300+ and pencil to a $5M all-in — built on public records, no MLS license, no scraping.

**Version:** 1.0 (lean) · **Date:** Aug 1, 2026 · **Audience:** the six of us · **Model:** pooled investment, one buy box

> Private build spec — not for distribution.

| At a glance | |
|---|---|
| Recurring cost | ~$0–100 / mo, all-in |
| Investors | 6, one shared strategy |
| Stack | One process, one Postgres |
| MVP | ~5 focused weeks |

---

## 1. The group model

One pooled strategy, one buy box, six notification endpoints. Because the investment is shared, everything per-user disappears — no individual filters, no tenancy, no fan-out logic.

- **Shared deal pipeline, not personal portfolios.** The board runs `New → Reviewing → Site Visit → Offer → Closed / Passed` with inline comments and a yes/no/maybe vote so the six of us converge on what to pursue.
- **The Telegram group is the primary surface.** Deals land in the group, discussion happens inline, decisions get recorded.
- **No OAuth / RBAC / JWT.** Six people = an allowlist of Telegram IDs. Real auth arrives only if the dashboard ever goes public.

> **Decide off-app:** Pooling money among six friends implies an LLC/JV + operating agreement, and if any member is passive it can raise securities questions. That's a lawyer conversation, not an app feature — flagged so it doesn't surprise us. The app is only the shared research-and-decision record for that one entity. *(Not legal advice.)*

---

## 2. Selection & notification criteria

**Selection and notification are two different gates.** Everything that clears selection enters the pipeline quietly; only a subset crosses the notification threshold and interrupts the group. Selection runs in three layers.

### Layer 1 — Buy box (hard filter, pass/fail)

| Criterion | Threshold | Note |
|---|---|---|
| Geography | DFW + ring counties | Dallas, Tarrant, Collin, Denton, Ellis, Johnson, Kaufman, Parker, Rockwall, Wise |
| Land parcel | ≥ 5 acres | Overall parcel size (min) |
| Existing structure | ≥ 15,000 SF | Must support 300+ guests |
| Purchase price | ≤ $4M | Modeled at negotiated price, not list |
| **Total all-in** | **≤ $5M** | **Binding constraint** — purchase + conversion + working capital to break-even |
| Property type | Barn / church / commercial | Existing building to retrofit — no raw land, no ground-up |
| Capacity | 300+ guests | Parking (~100 spaces), ADA restrooms, HVAC, egress |
| Go-live | ≤ 6 months | Favors assembly-zoned, structurally sound, utility-served |
| Hard exclusions | — | Flood AE/AO · Superfund ≤ 1 mi · condemnation · saturated sub-market (Layer 3) |

> **The coupled budget drives most decisions.** $4M purchase *and* $5M all-in means **conversion + working capital ≤ ($5M − negotiated price)**. At a $4M buy that leaves only ~$1M for a 300-guest retrofit + ramp — rarely enough, so the $5M cap will reject most top-of-budget purchases. The sweet spot is a **~$2–3M purchase** leaving $2–3M for conversion + working capital. RealtyDog shows this headroom on every deal card.

### Layer 2 — Motivation score (off-market ranker)

Ranks which qualifying owners to pursue first, now headlined by the **distressed non-profit** signal (full rubric in Section 8). Bucketed **HOT ≥ 60 · WARM 30–59 · COLD < 30**.

### Layer 3 — Financial & market qualification (hard gate, post-enrichment)

The pro-forma is part of selection, not just analysis. A property must clear *all* of:

- **Return gate:** at standard assumptions, **Year-2 break-even AND Year-3 EBITDA ≥ 10%**, within the $5M all-in. Can't model to it → rejected.
- **Negotiated price:** the buy is priced at an expected market-condition discount to list/assessed, not list. Pre-filter screens list/assessed ≤ ~$4.5–5M, then the hard test runs on the modeled negotiated number.
- **Capacity to 300+:** any retrofit cost to reach parking / restroom / HVAC / egress for 300 counts against the $5M.
- **Competitor demand:** **reject** a sub-market where nearby venues run **< 40% utilization** (estimated from review cadence + booking-calendar availability).
- **Retrofit feasibility ≤ 6 months:** rezoning-required → excluded; CUP-required → amber timeline-risk flag.

> **Two honest flags.** *6-month go-live is aggressive* for 300+ capacity — a CUP alone is 60–120 days, so this works as a selection *preference* (favor already-assembly-zoned, utility-served buildings), not a promise. *Competitor utilization is an estimate*, not published data — treat < 40% as an amber "verify" flag, sanity-checked against a few known venues before it hard-rejects a sub-market.

### Notification tiers

| Tier | Trigger | Channel |
|---|---|---|
| **Instant** | New buy-box parcel that's Hot (≥ 60), or a new on-market buy-box listing that clears the Layer-3 return gate | Telegram group, next scan |
| **Nightly digest** | New Warm prospects + everything new that passed the buy box | Telegram + email, 8 AM |
| **On-demand** | `/analyze`, `/tip`, `/prospects` | Whoever asked |

**Cold (< 30) is selected but never notified** — it lives in the universe and surfaces only via `/prospects`. A dedup ledger (parcel + signal) prevents notifying the same property twice for the same trigger. All thresholds are per-group config.

---

## 3. Architecture — the whole thing

- **One service.** FastAPI + APScheduler in a single process. Scheduler jobs: ingest → filter → enrich → score → digest.
- **One database.** Postgres with PostGIS (geo), JSONB (raw payloads), `pg_trgm` (fuzzy dedup + search). This alone replaces PostgreSQL + MongoDB + Elasticsearch + Pinecone + Snowflake from the original.
- **S3 / Backblaze B2** for property photos — the only thing Postgres shouldn't hold.
- **Telegram-first.** Free, rich cards, inline buttons, group-native. No Twilio/SMS — it's the one paid, rate-limited, verification-heavy channel and the group doesn't need it. Free-tier email for the daily digest.
- **Deploy** on Railway/Fly, single process, `alembic upgrade head` on deploy.

### Monthly cost

| Line | Choice | Cost |
|---|---|---|
| Compute | Single process, Railway/Fly | $5–20 |
| Database | Managed Postgres + PostGIS | $0–25 |
| Photo storage | Backblaze B2 / S3 | $1–5 |
| Maps / proximity | Google Maps, cached 7d | $0–30 |
| LLM narrative | Cheap model, on-demand | $1–10 |
| Skip-trace | Per-hit, hot leads only | pennies |
| Telegram + email | Free tiers | $0 |
| **Total** | all-in | **~$0–100** |

---

## 4. Data access — legal, and off-market first

None of us is a licensed realtor, so legitimate MLS/RESO access is effectively closed and scraping LoopNet/Crexi/Zillow is a ToS/CFAA problem. Good news: the channels open to an unlicensed buyer group are strong, and they reshape the product around its real moat.

> **The reframe:** There is no database of "off-market properties for sale." What exists is the **full parcel universe** (county appraisal data) + **motivation signals** (distress & ownership) + **a way to reach the owner**. Off-market discovery = filter the universe to our buy box, rank by likelihood-to-sell, and reach out. The app computes the ranking and runs the outreach.

**The mail-first insight (this is what avoids the subscription):** Direct mail — the safest, TCPA-clean channel — needs only the owner's **mailing address**, and **CAD data already contains it for free**. So we mail first at $0 skip-tracing cost, and only pay per-hit (~$0.10–0.25) to skip-trace the handful of hot leads we decide to call. No PropStream monthly floor.

### Free source stack

| Source | What it gives | Access |
|---|---|---|
| County Appraisal Districts (DCAD, TAD, Collin, Denton…) | Parcel universe + owner + mailing address | Public / bulk |
| Tax-foreclosure firms (Linebarger/LGBS, MVBA, Perdue Brandon) | Upcoming tax-sale lists, DFW-wide | Free web/PDF |
| County clerk — Substitute Trustee notices | Pre-foreclosure (first-Tuesday sales) | Public |
| Probate court + Lis Pendens | Estates, litigation pressure | Public search |
| City open-data portals | Code violations | Free |
| IRS Form 990 (ProPublica Nonprofit Explorer) | Non-profit 5-yr financials & net-asset trend | Free API |

**Outreach stays clean:** Using public records is fine; the regulated part is *contact method*. **Direct mail = safest** (no consent needed). Calls/texts to cell phones trigger TCPA + the Do-Not-Call list — skip-trace gives numbers, but *how* we dial is the regulated part. Buying directly to hold needs no license; wholesaling (contract-and-assign) is where TX licensing creeps in, so we avoid it.

---

## 5. Ingestion jobs — ordered by yield ÷ effort

Pre-aggregated distress lists (someone already did the filtering) beat raw county dumps, so they come online first.

**Job 0 — Per-county access spike (do first).** Before any parsers, confirm what each county publishes: bulk download vs. search-only, whether it includes owner mailing address, the physical fields (acres, improvement SF, land-use, year built), the format, and refresh cadence. Record findings in a `sources` config row per county. Expect every county to differ — that's why it's a spike, not an assumption.

| # | Job | Source | Cadence | Priority |
|---|---|---|---|---|
| 1 | Tax-sale lists | LGBS / MVBA / Perdue Brandon (HTML + PDF) | Weekly | P0 |
| 2 | CAD parcel universe | Bulk CAD, 2–3 primary counties | Monthly | P0 |
| 3 | Foreclosure postings | County clerk / trustee notices | Weekly | P1 |
| 4 | Probate + Lis Pendens | Clerk / probate search | Weekly | P1 |
| 5 | Code violations | City open-data portals | Weekly | P2 |
| 6 | Skip-trace (hot leads) | Pay-per-hit API | On demand | P2 |
| 7 | Craigslist RSS | Per-search RSS feeds (see Section 6) | Every 6h | P1 |
| 8 | Non-profit financials | IRS Form 990 via ProPublica API | Monthly | P1 |

**Job 8 — Distressed non-profit owners (the new edge).** Input #1, and arguably RealtyDog's sharpest lane. Cross the CAD **tax-exempt / non-profit owners** (exempt flag on the appraisal roll) against **IRS Form 990** financials via the free **ProPublica Nonprofit Explorer API** — 5 years of revenue, expenses, and net assets per EIN. Flag orgs with sustained losses or a declining net-asset trend, write a `signal_type='nonprofit_distress'` row (+35), and match to `parcels` by owner name / EIN. Depends on Job 2 (needs the CAD universe loaded to cross-reference). Churches are the exception — they don't file 990; use the proxy path noted in Section 8.

*Gotchas:* tax-sale rows carry cause numbers & legal descriptions, not always clean addresses — match by APN/legal description, not address alone. Probate/estate name-matching is fuzzy — store a `match_confidence` and never hard-merge below threshold.

---

## 6. Social channels — what can actually auto-flow

Two very different jobs hide under "social media info": **sourcing** (find properties owners are quietly selling on FB/Craigslist/Nextdoor) and **market intel** (competitor-venue pricing, wedding-demand sentiment). Fully-automatic ingestion of most social platforms means scraping, which is a ToS/CFAA/fragility problem. So we split by what's genuinely clean to automate.

| Platform | Value | Auto-flow? | Approach |
|---|---|---|---|
| Craigslist | FSBO land / commercial | clean | Per-search **RSS feeds** — supported, low-fragility |
| Facebook Marketplace / groups | FSBO, off-market land | scraping | `/tip` forward — no legal API |
| Nextdoor | Hyperlocal owner posts | scraping | `/tip` forward |
| LinkedIn | Broker pocket-listings | litigated | `/tip` forward (hiQ risk) |
| Instagram / TikTok / Google reviews | Venue demand & comp pricing | later | Market-intel phase, deferred |

**The clean auto path — Craigslist RSS (Job 7):** Craigslist exposes an RSS feed on any search URL. We register buy-box searches (land / commercial, acreage + price band, each target county), poll every few hours, keyword-filter to the buy box, and drop matches into `deals` as `source='social'`. No scraping, no proxies — a real feed.

> **The "automatic" for the rest:** The six of us *are* a social sensor network. A `/tip <link or photo>` command lets any member forward a Facebook / Nextdoor / LinkedIn find; it enters the same prospect/deal pipeline, gets `/analyze`'d, and shows up on the board. That's social "flowing in" continuously without the fragility of scraping.

If we later decide fully-automatic FB/Nextdoor ingestion is worth the fragility, isolate it behind its own failure boundary so a broken selector can never take the pipeline down. Market-intel social listening is a separate, lower-priority phase.

---

## 7. Data model — one Postgres

PostGIS for geo, JSONB for raw/flexible fields, `pg_trgm` GIN indexes for fuzzy owner/address matching instead of a separate search engine.

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- the six of us
CREATE TABLE users (
  id           BIGSERIAL PRIMARY KEY,
  handle       TEXT NOT NULL,
  telegram_id  TEXT UNIQUE,
  is_owner     BOOLEAN NOT NULL DEFAULT FALSE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- per-county / per-feed access config (filled by Job 0)
CREATE TABLE sources (
  id            BIGSERIAL PRIMARY KEY,
  name          TEXT NOT NULL UNIQUE,      -- 'dcad_bulk','lgbs_tax_sale'
  county        TEXT,
  kind          TEXT NOT NULL,             -- 'cad'|'tax_sale'|'foreclosure'|...
  access_method TEXT,                      -- 'bulk_csv'|'api'|'html'|'pdf'
  config        JSONB NOT NULL DEFAULT '{}',
  last_run_at   TIMESTAMPTZ,
  last_status   TEXT
);

-- the universe (from CAD) = every off-market candidate
CREATE TABLE parcels (
  id               BIGSERIAL PRIMARY KEY,
  apn              TEXT NOT NULL,
  county           TEXT NOT NULL,
  situs_address    TEXT, city TEXT, zip TEXT,
  lat DOUBLE PRECISION, lon DOUBLE PRECISION,
  geo_point        GEOGRAPHY(POINT, 4326),
  owner_name       TEXT,
  owner_type       TEXT,                    -- 'person'|'entity'|'estate'
  tax_exempt       BOOLEAN,                 -- from CAD exempt flag
  nonprofit_ein    TEXT,                    -- matched to IRS 990 (Job 8)
  owner_mailing_address TEXT,
  owner_mailing_state   TEXT,
  acres            NUMERIC(10,2),
  improvement_sf   INTEGER,
  land_use_code    TEXT,
  year_built       INTEGER,
  assessed_value   NUMERIC(14,2),
  last_sale_date   DATE, last_sale_price NUMERIC(14,2),
  absentee         BOOLEAN,                 -- derived: mailing != situs
  tenure_years     INTEGER,                 -- derived from last_sale_date
  meets_buy_box    BOOLEAN NOT NULL DEFAULT FALSE,
  first_seen       TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_updated     TIMESTAMPTZ NOT NULL DEFAULT now(),
  source           TEXT,
  UNIQUE (county, apn)
);
CREATE INDEX idx_parcels_geo    ON parcels USING GIST (geo_point);
CREATE INDEX idx_parcels_buybox ON parcels (meets_buy_box) WHERE meets_buy_box;
CREATE INDEX idx_parcels_owner  ON parcels USING GIN (owner_name gin_trgm_ops);

-- motivation signals, many per parcel
CREATE TABLE distress_signals (
  id            BIGSERIAL PRIMARY KEY,
  parcel_id     BIGINT REFERENCES parcels(id) ON DELETE SET NULL,
  signal_type   TEXT NOT NULL,   -- 'tax_sale'|'foreclosure_posting'|'probate'|'nonprofit_distress'|...
  source        TEXT NOT NULL,
  event_date    DATE, sale_date DATE,
  amount        NUMERIC(14,2),
  cause_number  TEXT,
  match_confidence NUMERIC(4,3),
  raw           JSONB NOT NULL DEFAULT '{}',
  ingested_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_signals_parcel ON distress_signals(parcel_id);

-- buy-box parcels worth outreach (scored)
CREATE TABLE prospects (
  id                BIGSERIAL PRIMARY KEY,
  parcel_id         BIGINT NOT NULL UNIQUE REFERENCES parcels(id) ON DELETE CASCADE,
  motivation_score  INTEGER NOT NULL DEFAULT 0,
  score_breakdown   JSONB NOT NULL DEFAULT '{}',
  status            TEXT NOT NULL DEFAULT 'prospect',
                    -- prospect|contacted|responded|analyzing|offer|passed
  assigned_to       BIGINT REFERENCES users(id),
  last_contacted_at TIMESTAMPTZ,
  contact_method    TEXT, notes TEXT,
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_prospects_score ON prospects(motivation_score DESC);

-- anything /analyze'd (on- or off-market)
CREATE TABLE deals (
  id              BIGSERIAL PRIMARY KEY,
  parcel_id       BIGINT REFERENCES parcels(id) ON DELETE SET NULL,
  listing_url     TEXT,
  enrichment      JSONB NOT NULL DEFAULT '{}',
  proforma        JSONB NOT NULL DEFAULT '{}',
  rubric          JSONB NOT NULL DEFAULT '{}',
  all_in_cost       NUMERIC(14,2),         -- purchase + conversion + working capital
  breakeven_year    INTEGER,               -- target: <= 2
  y3_ebitda_pct     NUMERIC(5,2),          -- target: >= 10.0
  meets_return_gate BOOLEAN,               -- Yr2 break-even AND Yr3 EBITDA >= 10%
  pipeline_status TEXT NOT NULL DEFAULT 'new',
                  -- new|reviewing|site_visit|offer|closed|passed
  created_by      BIGINT REFERENCES users(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (parcel_id IS NOT NULL OR listing_url IS NOT NULL)
);

-- who contacted whom, and the response
CREATE TABLE outreach_log (
  id          BIGSERIAL PRIMARY KEY,
  prospect_id BIGINT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
  user_id     BIGINT REFERENCES users(id),
  method      TEXT NOT NULL,          -- 'mail'|'call'|'email'
  sent_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  response    TEXT, response_at TIMESTAMPTZ
);

-- group decision on a deal
CREATE TABLE votes (
  id         BIGSERIAL PRIMARY KEY,
  deal_id    BIGINT NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
  user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  vote       TEXT NOT NULL,          -- 'yes'|'no'|'maybe'
  comment    TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (deal_id, user_id)
);
```

*Cross-source dedup:* match on `apn` first (authoritative), then normalized address + `pg_trgm` fuzzy score above threshold. No Elasticsearch.

---

## 8. Motivation score — an explainable rubric

Kept as a transparent point-sum, never a black box, so the group trusts it and we can tune it against real response data later. The `score_breakdown` JSONB always records *why*.

| Signal | Points | Why |
|---|---|---|
| Tax-sale / tax delinquent | +40 | Strongest — active financial distress |
| Distressed non-profit owner (5-yr losses) | +35 | Cash-bleeding non-profit on acreage — motivated, often below-market |
| Foreclosure posting | +35 | Time-pressured seller |
| Probate / estate owner | +25 | Heirs commonly sell |
| Lis pendens | +20 | Litigation / divorce pressure |
| Code violation | +15 | Can't / won't maintain |
| Absentee owner | +15 | Lower attachment to property |
| Out-of-state owner | +10 | Wants to divest distant asset |
| Tenure ≥ 20 years | +10 | High equity, life-stage transitions |

Signals stack (a tax-sale + absentee + estate owner is very hot). Bucketed: **HOT ≥ 60 · WARM 30–59 · COLD < 30**.

**Non-profit distress detection:** cross CAD tax-exempt owners against IRS Form 990 financials (free ProPublica Nonprofit Explorer API) — flag sustained losses or declining net assets over 5 years. Caveat: **churches don't file 990**, so for them lean on proxies (denominational closure lists, deferred-maintenance/lien signals, ChurchRealty listings) and tag which basis was used.

Weights are starting guesses. After a few mail campaigns, look at which signals actually produced responses (via `outreach_log`) and adjust — the one place we get a real feedback signal here.

---

## 9. Scheduler & commands

### Scheduled jobs (APScheduler)

| Cadence | Job |
|---|---|
| Weekly | Tax-sale lists (Job 1) |
| Weekly | Foreclosure postings (Job 3) |
| Weekly | Probate + lis pendens (Job 4) |
| Every 6h | Craigslist RSS feeds (Job 7, keyword-filtered to buy box) |
| Monthly | CAD full refresh (Job 2) |
| Monthly | Non-profit 990 refresh + distress re-score (Job 8) |
| Nightly | Recompute motivation scores + Layer-3 return gate → emit new-hot-prospect digest to the group |

### Telegram commands

- `/analyze <url | apn>` — full deal card: enrichment + rubric + ramp-aware pro-forma. *The pull-first core.*
- `/tip <link | photo>` — forward a social find (FB / Nextdoor / LinkedIn) into the pipeline as `source='social'`.
- `/prospects [hot|warm]` — current outreach list, ranked by motivation score.
- `/pipeline` — the group deal board by stage.
- `/vote <deal>` — yes / no / maybe via inline buttons.
- **Mail-merge export** — CSV of hot prospects (name + CAD mailing address) for a direct-mail run.

---

## 10. Build roadmap

- **Week 0** — Job 0 spike: confirm CAD access per county. Stand up Postgres + schema, one-process FastAPI + APScheduler skeleton, Telegram group wired.
- **Week 1** — Job 1 (tax-sale lists) + Job 2 (CAD universe, 2–3 counties) + motivation score v1 + nightly hot-prospect digest. → *Real off-market leads flowing by end of week 1.*
- **Week 2** — Jobs 3–4 (foreclosure / probate / lis pendens) + cross-source dedup + outreach pipeline + mail-merge export. → *First mail campaign goes out.*
- **Week 3** — `/analyze` (enrichment + pro-forma) + ring counties + `/pipeline` + `/vote`.
- **Week 4** — Per-hit skip-trace for the call list, polish, tune score weights against early response data.

---

## 11. Design principles

- **Pro-forma models the ramp.** Year-1/2/3 columns to the targets (Year-2 break-even, Year-3 EBITDA ≥ 10%); working capital to break-even folded into the $5M all-in; conversion-cost scaling is fixed vs. occupancy-driven, not linear-in-SF; the yield is labeled a development yield, not a cap rate.
- **Scoring is an explainable rubric, not a score.** Traffic-light sub-scores, not a false-precision 0–100 — at ~1–3 closed deals/year an "accuracy %" can't be validated.
- **Zoning is a research checklist, not a verdict.** Parcel + jurisdiction + code + planning link for a human to verify — an automated permitted-use determination is a liability line.
- **Use a buyer's agent for MLS coverage.** Even unlicensed, the group can work with one who legally sets up MLS saved-searches and forwards matches — free MLS coverage without building anything.

---

## 12. Open decisions before Week 0

1. **Which 2–3 counties are primary?** Drives the Job 0 spike and the first CAD ingestion.
2. **Who owns the direct-mail send?** The pipeline's `assigned_to` needs a real person.
3. **Entity + operating agreement.** Shapes how the pipeline records a decision — who votes, and what "approved" means.
4. **CAD access per county** (bulk vs. search-only vs. paid) — the first thing to verify, because it's the whole backbone.
5. **Standard assumptions for the return gate.** Negotiated-price discount %, conversion $/SF, and the ramp curve that define "Year-2 break-even, Year-3 10% EBITDA" — these literally decide what selects.
6. **Validate the competitor-utilization estimate** against 3–5 known DFW venues before it's allowed to hard-reject a sub-market.

---

## 13. Standard financial assumptions (the return gate)

These are the defaults the Layer-3 return gate runs on every enriched property. **All are configurable**, but a property qualifies only if it models to **Year-2 break-even AND Year-3 EBITDA ≥ 10%** within the **$5M all-in**. Numbers below are starting estimates for a ~15,000 SF, 300-guest DFW venue — tighten them against the first real deal.

### Acquisition & financing

| Assumption | Default | Note |
|---|---|---|
| Negotiated price | list/assessed × 0.90 | Distressed / non-profit seller × 0.85; hard cap $4M |
| Closing + soft costs | 3% | Of purchase |
| Financing | 70% LTV | Of purchase + conversion (conventional commercial) |
| Rate / amortization | 8.0% / 25 yr | SBA 504 lowers this materially — big lever |
| Equity (pooled) | ~30% | The group's cash in |

### Conversion capex by property type (~15,000 SF → 300-guest, incl. 10% contingency)

| Type | Total | Why |
|---|---|---|
| Church | $1.2–1.6M | Assembly-ready; often has restrooms, parking, kitchen |
| Commercial building | $1.8–2.2M | Some infrastructure; needs assembly build-out |
| Warehouse | $2.0–2.5M | Shell — needs nearly everything |
| Barn / barndominium | $2.2–2.8M | Rural; may lack sewer/utilities |

Line items (scaled + contingency): structural, HVAC, 200A+ electrical, ADA restrooms, fire suppression, kitchen build-out, flooring/interior, parking/grading, landscape, permits/soft costs. Fixed-cost components (fire riser, service upgrade, kitchen) do *not* scale linearly with SF.

### Working capital & pre-opening

| Line | Default |
|---|---|
| Pre-opening (branding, website, photography, launch marketing) | $150,000 |
| Operating reserve (carries the Year-1 ramp loss) | $200–250,000 |
| **Working-capital total** | **~$350–400K** |

### Revenue model (stabilized = Year 3) & ramp

| Segment | Volume | Avg | Stabilized |
|---|---|---|---|
| Weddings | 45 / yr | $15,000 | $675,000 |
| Corporate / galas | 20 / yr | $7,000 | $140,000 |
| Private parties | 30 / yr | $5,000 | $150,000 |
| Ancillary (bar/catering margin, vendor fees, rentals) | — | — | $285,000 |
| **Stabilized gross** | ~95 events | — | **$1,250,000** |

**Ramp:** Year 1 = 40% of stabilized, Year 2 = 75%, Year 3 = 100% — venues book 9–18 months out, so Year 1 is nearly empty and the first full booking cycle lands in Year 2. Seasonal skew (spring/fall peak) is absorbed in the annual figures.

### Operating expenses

| Line | Default |
|---|---|
| Variable OpEx (per-event staffing, supplies) | 30% of revenue |
| Marketing (ongoing) | 6% of revenue |
| Replacement reserve | 2% of revenue |
| GM + admin salaries | $120,000 |
| Property tax | $70,000 |
| Insurance (venue liability + property) | $25,000 |
| Utilities | $30,000 |
| Maintenance / grounds | $35,000 |

### Worked base case — proof it pencils

A $5M all-in on a $2.5M church/commercial retrofit:

| All-in | Amount |
|---|---|
| Purchase (negotiated) | $2,500,000 |
| Conversion capex (incl. 10% contingency) | $2,000,000 |
| Closing + soft costs | $150,000 |
| Working capital + pre-opening | $350,000 |
| **Total all-in** | **$5,000,000** |
| Debt (70% of $4.5M) | $3,150,000 |
| Equity (pooled — ~$308K × 6) | $1,850,000 |
| Annual debt service (8%, 25 yr) | ~$291,700 |

| 3-year P&L | Yr 1 (40%) | Yr 2 (75%) | Yr 3 (100%) |
|---|---|---|---|
| Gross revenue | $500,000 | $937,500 | $1,250,000 |
| Total OpEx | $470,000 | $636,250 | $755,000 |
| EBITDA | $30,000 | $301,250 | $495,000 |
| EBITDA margin | 6% | 32% | 40% |
| Debt service | ($291,700) | ($291,700) | ($291,700) |
| **Cash flow** | ($261,700) | **+$9,550** | **+$203,300** |

**Gate check:** Year-2 cash flow **+$9,550 → break-even ✓** · Year-3 EBITDA margin **40% ≥ 10% ✓** · Year-1 loss ($262K) covered by the $350K working-capital reserve.

> **The honest read on these targets:** **Year-2 break-even is the binding constraint, not the 10% EBITDA** — a healthy venue clears 30–40% EBITDA by Year 3, so that gate is easy; the hard one is covering debt service by Year 2 while still ramping. It pencils here *only* because the purchase stays at $2.5M (modest leverage) and revenue ramps to 75% by Year 2 — optimistic given 9–18-month booking lead times. Three levers decide it: **keep the purchase low** (more equity, less debt service), **SBA 504 financing** (cuts debt service materially), and **property type** (a barn/warehouse's higher conversion cost forces a lower purchase to stay under $5M). A high-purchase, high-leverage deal misses Year-2 break-even even on a great building — which is exactly what the gate is there to catch.

---

*RealtyDog · lean build spec v1.0 · internal working document for the partnership*
