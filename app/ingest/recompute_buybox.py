"""Recompute meets_buy_box from stored parcel fields — NO API fetch, seconds not minutes.

Use this after a buy-box logic change (max acres, owner exclusions, assessed ceiling, ...)
instead of a full cad_refresh. All inputs meets_buy_box needs — county, acres, property_type,
assessed_value, owner_name — are already persisted, so we just re-evaluate and UPDATE.
"""
from __future__ import annotations

import logging

from sqlalchemy import text

from app.db import engine
from app.ingest.parcels import RawParcel, meets_buy_box

log = logging.getLogger("realtydog.recompute")

_SELECT = text("SELECT id, county, acres, property_type, assessed_value, owner_name FROM parcels")
_UPDATE = text("UPDATE parcels SET meets_buy_box = :mbb, last_updated = now() WHERE id = :id")


def recompute_buy_box() -> tuple[int, int]:
    """Re-evaluate meets_buy_box for every parcel. Returns (total, candidates)."""
    candidates = 0
    with engine.begin() as conn:
        rows = conn.execute(_SELECT).fetchall()
        for r in rows:
            p = RawParcel(
                apn="",
                county=r.county,
                acres=float(r.acres) if r.acres is not None else None,
                property_type=r.property_type,
                assessed_value=float(r.assessed_value) if r.assessed_value is not None else None,
                owner_name=r.owner_name,
            )
            mbb = meets_buy_box(p)
            candidates += int(mbb)
            conn.execute(_UPDATE, {"mbb": mbb, "id": r.id})
    log.info("recompute_buy_box: %d parcels, %d candidates", len(rows), candidates)
    return len(rows), candidates


if __name__ == "__main__":  # `python -m app.ingest.recompute_buybox`
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    n, c = recompute_buy_box()
    print(f"recompute: {n} parcels, {c} candidates")
