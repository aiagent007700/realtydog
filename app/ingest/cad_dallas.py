"""Dallas Central Appraisal District (DCAD) parcel ingestion.

DCAD publishes a free bulk ZIP of comma-delimited files (dallascad.org/dataproducts.aspx)
with field-reference docs inside the ZIP. The exact filenames and column names are NOT
yet confirmed (SPIKE-000 residual) — do NOT hard-code guessed columns here. This adapter
provides the structure; the FIELD_MAP + file layout must be filled from the reference doc
before it is enabled. Until then it yields nothing (logged), so wiring it into the
scheduler is harmless.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator

from app.ingest.parcels import RawParcel

log = logging.getLogger("realtydog.cad.dallas")

# Flip to True once the download URL, ZIP member filenames, and column names below are
# confirmed against the DCAD data-products reference doc.
FIELD_MAP_CONFIRMED = False

# TODO(JOB-002 / SPIKE-000): confirm from the DCAD reference doc, then implement
# download -> unzip -> read ownership/appraisal CSVs -> map to RawParcel.
#   apn                    <- account number column
#   owner_name             <- owner column
#   owner_mailing_address  <- owner mailing address column(s)
#   acres / improvement_sf <- land area / improvement SF columns
#   land_use_code          <- state/local use code column (feeds property_type + tax-exempt)


def fetch_dallas_parcels() -> Iterator[RawParcel]:
    if not FIELD_MAP_CONFIRMED:
        log.info("DCAD adapter pending field-map confirmation (SPIKE-000 residual) — skipping")
        return iter(())
    return iter(())  # implemented once FIELD_MAP_CONFIRMED
