"""Initial RealtyDog schema (README §7).

Revision ID: 0001
Revises:
Create Date: 2026-08-01
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute(
        """
        CREATE TABLE users (
          id           BIGSERIAL PRIMARY KEY,
          handle       TEXT NOT NULL,
          telegram_id  TEXT UNIQUE,
          is_owner     BOOLEAN NOT NULL DEFAULT FALSE,
          created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE sources (
          id            BIGSERIAL PRIMARY KEY,
          name          TEXT NOT NULL UNIQUE,
          county        TEXT,
          kind          TEXT NOT NULL,
          access_method TEXT,
          config        JSONB NOT NULL DEFAULT '{}',
          last_run_at   TIMESTAMPTZ,
          last_status   TEXT
        )
        """
    )

    op.execute(
        """
        CREATE TABLE parcels (
          id               BIGSERIAL PRIMARY KEY,
          apn              TEXT NOT NULL,
          county           TEXT NOT NULL,
          situs_address    TEXT,
          city             TEXT,
          zip              TEXT,
          lat              DOUBLE PRECISION,
          lon              DOUBLE PRECISION,
          geo_point        GEOGRAPHY(POINT, 4326),
          owner_name       TEXT,
          owner_type       TEXT,
          tax_exempt       BOOLEAN,
          nonprofit_ein    TEXT,
          owner_mailing_address TEXT,
          owner_mailing_state   TEXT,
          acres            NUMERIC(10,2),
          improvement_sf   INTEGER,
          land_use_code    TEXT,
          year_built       INTEGER,
          assessed_value   NUMERIC(14,2),
          last_sale_date   DATE,
          last_sale_price  NUMERIC(14,2),
          absentee         BOOLEAN,
          tenure_years     INTEGER,
          meets_buy_box    BOOLEAN NOT NULL DEFAULT FALSE,
          first_seen       TIMESTAMPTZ NOT NULL DEFAULT now(),
          last_updated     TIMESTAMPTZ NOT NULL DEFAULT now(),
          source           TEXT,
          UNIQUE (county, apn)
        )
        """
    )
    op.execute("CREATE INDEX idx_parcels_geo    ON parcels USING GIST (geo_point)")
    op.execute("CREATE INDEX idx_parcels_buybox ON parcels (meets_buy_box) WHERE meets_buy_box")
    op.execute("CREATE INDEX idx_parcels_owner  ON parcels USING GIN (owner_name gin_trgm_ops)")

    op.execute(
        """
        CREATE TABLE distress_signals (
          id            BIGSERIAL PRIMARY KEY,
          parcel_id     BIGINT REFERENCES parcels(id) ON DELETE SET NULL,
          signal_type   TEXT NOT NULL,
          source        TEXT NOT NULL,
          event_date    DATE,
          sale_date     DATE,
          amount        NUMERIC(14,2),
          cause_number  TEXT,
          match_confidence NUMERIC(4,3),
          raw           JSONB NOT NULL DEFAULT '{}',
          ingested_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_signals_parcel ON distress_signals(parcel_id)")

    op.execute(
        """
        CREATE TABLE prospects (
          id                BIGSERIAL PRIMARY KEY,
          parcel_id         BIGINT NOT NULL UNIQUE REFERENCES parcels(id) ON DELETE CASCADE,
          motivation_score  INTEGER NOT NULL DEFAULT 0,
          score_breakdown   JSONB NOT NULL DEFAULT '{}',
          status            TEXT NOT NULL DEFAULT 'prospect',
          assigned_to       BIGINT REFERENCES users(id),
          last_contacted_at TIMESTAMPTZ,
          contact_method    TEXT,
          notes             TEXT,
          updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_prospects_score ON prospects(motivation_score DESC)")

    op.execute(
        """
        CREATE TABLE deals (
          id              BIGSERIAL PRIMARY KEY,
          parcel_id       BIGINT REFERENCES parcels(id) ON DELETE SET NULL,
          listing_url     TEXT,
          enrichment      JSONB NOT NULL DEFAULT '{}',
          proforma        JSONB NOT NULL DEFAULT '{}',
          rubric          JSONB NOT NULL DEFAULT '{}',
          all_in_cost       NUMERIC(14,2),
          breakeven_year    INTEGER,
          y3_ebitda_pct     NUMERIC(5,2),
          meets_return_gate BOOLEAN,
          pipeline_status TEXT NOT NULL DEFAULT 'new',
          created_by      BIGINT REFERENCES users(id),
          created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
          CHECK (parcel_id IS NOT NULL OR listing_url IS NOT NULL)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE outreach_log (
          id          BIGSERIAL PRIMARY KEY,
          prospect_id BIGINT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
          user_id     BIGINT REFERENCES users(id),
          method      TEXT NOT NULL,
          sent_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
          response    TEXT,
          response_at TIMESTAMPTZ
        )
        """
    )

    op.execute(
        """
        CREATE TABLE votes (
          id         BIGSERIAL PRIMARY KEY,
          deal_id    BIGINT NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
          user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          vote       TEXT NOT NULL,
          comment    TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE (deal_id, user_id)
        )
        """
    )


def downgrade() -> None:
    for tbl in (
        "votes",
        "outreach_log",
        "deals",
        "prospects",
        "distress_signals",
        "parcels",
        "sources",
        "users",
    ):
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
