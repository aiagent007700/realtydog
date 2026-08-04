"""OUTREACH-001 — mail-merge export of the target list for a direct-mail run.

Segments to the two real off-market profiles — individually/family-owned parcels
(`owner_type='person'`) and churches/foundations — because the corporate-commercial /
industrial residue can't be cleanly rule-filtered (a state code can't tell a convertible
warehouse from a power plant). Dedupes to ONE row per owner + mailing address (one letter
per owner, keeping their largest parcel), and writes the CAD mailing address so a direct-mail
run needs no skip-tracing. Ordered by motivation score then acreage.
"""
from __future__ import annotations

import csv
import datetime
import logging

from sqlalchemy import text

from app.db import engine

log = logging.getLogger("realtydog.outreach.mailmerge")

_QUERY = text(
    """
    SELECT * FROM (
      SELECT DISTINCT ON (pk.owner_name, pk.owner_mailing_address)
             pk.owner_name, pk.owner_mailing_address, pk.owner_mailing_state,
             pk.situs_address, pk.city, pk.zip, pk.acres, pk.property_type,
             pk.land_use_code, pk.assessed_value, pk.tax_exempt,
             COALESCE(pr.motivation_score, 0) AS motivation_score
      FROM parcels pk
      LEFT JOIN prospects pr ON pr.parcel_id = pk.id
      WHERE pk.meets_buy_box
        AND pk.owner_mailing_address IS NOT NULL
        AND (pk.owner_type = 'person'
             OR pk.owner_name ILIKE '%CHURCH%' OR pk.owner_name ILIKE '%BAPTIST%'
             OR pk.owner_name ILIKE '%METHODIST%' OR pk.owner_name ILIKE '%CATHOLIC%'
             OR pk.owner_name ILIKE '%PRESBYTERIAN%' OR pk.owner_name ILIKE '%LUTHERAN%'
             OR pk.owner_name ILIKE '%FOUND%')
      ORDER BY pk.owner_name, pk.owner_mailing_address, pk.acres DESC
    ) t
    ORDER BY motivation_score DESC, acres DESC
    """
)

_COLUMNS = [
    ("owner_name", "Owner Name"),
    ("owner_mailing_address", "Mailing Address"),
    ("owner_mailing_state", "Mailing State"),
    ("situs_address", "Property Address"),
    ("city", "City"),
    ("acres", "Acres"),
    ("property_type", "Type"),
    ("land_use_code", "State Use Code"),
    ("assessed_value", "Assessed Value"),
    ("tax_exempt", "Tax Exempt"),
    ("motivation_score", "Motivation Score"),
]


def fetch_target_rows() -> list[dict]:
    with engine.connect() as conn:
        return [dict(r._mapping) for r in conn.execute(_QUERY)]


def write_csv(rows: list[dict], path: str) -> int:
    """Write rows to a mail-merge CSV. String fields are stripped (CAD data is space-padded)."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([label for _, label in _COLUMNS])
        for r in rows:
            out = []
            for key, _ in _COLUMNS:
                val = r.get(key)
                out.append(val.strip() if isinstance(val, str) else val)
            writer.writerow(out)
    return len(rows)


def export_mail_merge(path: str | None = None) -> tuple[str, int]:
    path = path or f"realtydog_mail_merge_{datetime.date.today():%Y%m%d}.csv"
    n = write_csv(fetch_target_rows(), path)
    log.info("mail-merge export: %d owners -> %s", n, path)
    return path, n


if __name__ == "__main__":  # `python -m app.outreach.mail_merge`
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    p, count = export_mail_merge()
    print(f"mail-merge export: {count} owners written to {p}")
