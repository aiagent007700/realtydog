"""Job 2 driver: ingest the configured primary counties into `parcels`.

Runs each county adapter, normalizes, and upserts. Fail-open per county so one
county's outage can't sink the others.
"""
from __future__ import annotations

import logging

from app.ingest.cad_dallas import fetch_dallas_parcels
from app.ingest.cad_tarrant import fetch_tarrant_parcels
from app.ingest.parcels import normalize
from app.ingest.persist import upsert_parcels

log = logging.getLogger("realtydog.cad")

# county name -> parcel fetcher (primary counties: Dallas + Tarrant)
SOURCES = {
    "Tarrant": fetch_tarrant_parcels,
    "Dallas": fetch_dallas_parcels,
}


def run_cad_refresh() -> int:
    total = 0
    for county, fetch in SOURCES.items():
        try:
            written = upsert_parcels(normalize(p) for p in fetch())
            total += written
            log.info("cad_refresh %s: upserted %d parcels", county, written)
        except Exception as exc:  # noqa: BLE001 - fail open, per-county isolation
            log.warning("cad_refresh %s failed: %s", county, exc)
    log.info("cad_refresh done: total=%d parcels", total)
    return total
