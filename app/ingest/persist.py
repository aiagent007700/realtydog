"""Upsert normalized parcels into the `parcels` table (SQLAlchemy core, PostGIS).

Keyed on the schema's UNIQUE (county, apn). geo_point is built from lat/lon via PostGIS.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable

from sqlalchemy import text

from app.db import engine

log = logging.getLogger("realtydog.persist")

_UPSERT = text(
    """
    INSERT INTO parcels (
      apn, county, situs_address, city, zip, lat, lon, geo_point,
      owner_name, owner_type, owner_mailing_address, owner_mailing_state,
      acres, improvement_sf, land_use_code, year_built, assessed_value,
      last_sale_date, absentee, tenure_years, meets_buy_box, source, last_updated
    ) VALUES (
      :apn, :county, :situs_address, :city, :zip, :lat, :lon,
      CASE WHEN :lat IS NOT NULL AND :lon IS NOT NULL
           THEN ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography END,
      :owner_name, :owner_type, :owner_mailing_address, :owner_mailing_state,
      :acres, :improvement_sf, :land_use_code, :year_built, :assessed_value,
      :last_sale_date, :absentee, :tenure_years, :meets_buy_box, :source, now()
    )
    ON CONFLICT (county, apn) DO UPDATE SET
      situs_address = EXCLUDED.situs_address,
      city = EXCLUDED.city,
      zip = EXCLUDED.zip,
      lat = EXCLUDED.lat,
      lon = EXCLUDED.lon,
      geo_point = EXCLUDED.geo_point,
      owner_name = EXCLUDED.owner_name,
      owner_type = EXCLUDED.owner_type,
      owner_mailing_address = EXCLUDED.owner_mailing_address,
      acres = EXCLUDED.acres,
      improvement_sf = EXCLUDED.improvement_sf,
      land_use_code = EXCLUDED.land_use_code,
      year_built = EXCLUDED.year_built,
      assessed_value = EXCLUDED.assessed_value,
      last_sale_date = EXCLUDED.last_sale_date,
      absentee = EXCLUDED.absentee,
      tenure_years = EXCLUDED.tenure_years,
      meets_buy_box = EXCLUDED.meets_buy_box,
      last_updated = now()
    """
)


def upsert_parcels(rows: Iterable[dict], batch: int = 500) -> int:
    """Batch-upsert normalized parcel dicts. Returns the number of rows written."""
    written = 0
    buf: list[dict] = []
    with engine.begin() as conn:
        for row in rows:
            buf.append(row)
            if len(buf) >= batch:
                conn.execute(_UPSERT, buf)
                written += len(buf)
                buf = []
        if buf:
            conn.execute(_UPSERT, buf)
            written += len(buf)
    return written
