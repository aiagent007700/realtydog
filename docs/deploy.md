# Deploy runbook — INFRA-001

RealtyDog is one process + one Postgres (PostGIS). The migration is verified to render
clean DDL offline, so it applies as soon as `DATABASE_URL` points at a PostGIS database.

**Account steps are yours to do** (Supabase / Railway / Telegram signups can't be
automated). Everything else is copy-paste.

---

## 1. Database — Supabase (PostGIS, free tier)

1. Create a project at supabase.com (region close to DFW, e.g. `us-east-1`).
2. **Settings → Database → Connection string.** Use the **Session pooler** or **Direct**
   connection (port **5432**) — *not* the Transaction pooler (6543), which breaks Alembic.
3. Build the SQLAlchemy URL (note the `+psycopg2` driver and `sslmode=require`):
   ```
   postgresql+psycopg2://postgres:<PASSWORD>@db.<REF>.supabase.co:5432/postgres?sslmode=require
   ```
4. PostGIS: the migration runs `CREATE EXTENSION IF NOT EXISTS postgis`. If your DB role
   lacks permission, first enable it in **Database → Extensions → postgis**, then continue.

## 2. Telegram

1. In BotFather: `/newbot` → save the **bot token**.
2. Add the bot to your group; get the **group chat id** (e.g. via `@RawDataBot` or the
   `getUpdates` API). Collect the 6 members' Telegram user IDs for `ALLOWED_TELEGRAM_IDS`.

## 3. Run it locally (verify before deploying)

```bash
cp .env.example .env          # then fill DATABASE_URL (+ Telegram/keys as needed)
pip install -r requirements.txt
alembic upgrade head          # creates the schema + PostGIS/pg_trgm
uvicorn app.main:app          # http://localhost:8000/health -> {"db": true, "jobs": 7}
```

First live parcel ingest (Tarrant; pulls all >=5-acre parcels — takes a few minutes):

```bash
python -m app.ingest.cad_refresh
```

Then sanity-check the DB:

```sql
SELECT county, count(*), count(*) FILTER (WHERE meets_buy_box) AS candidates FROM parcels GROUP BY county;
-- Tarrant rows > 0; candidates are the church matches until JOB-002b is activated.
```

## 4. Deploy — Railway

1. New project → **Deploy from GitHub repo** → `aiagent007700/realtydog`.
2. **Variables:** set everything from `.env.example` (at minimum `DATABASE_URL`,
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_GROUP_CHAT_ID`, `ALLOWED_TELEGRAM_IDS`).
3. Deploy. `railway.toml` runs `alembic upgrade head` (preDeploy) then starts uvicorn.
4. Verify the service's `/health` returns `{"status":"ok","db":true,"jobs":7}`.

The scheduler then runs `job_cad_refresh` monthly; use `python -m app.ingest.cad_refresh`
(step 3) for an immediate first load.

---

## Notes

- Object storage (photos) isn't needed until enrichment (ENR-001) — skip the S3 vars for now.
- JOB-002b (commercial/farm classification) stays dormant until its column layout is
  confirmed (see `app/ingest/cad_tarrant_roll.py`); the first live run classifies churches only.
