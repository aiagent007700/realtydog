"""Tarrant Appraisal District (TAD) parcel ingestion via the ArcGIS FeatureServer.

Verified endpoint + field names (SPIKE-000, docs/data_sources.md):
  https://mapit.tarrantcounty.com/arcgis/rest/services/Dynamic/TADParcels/FeatureServer/0/query
Fields include: ACCOUNT, OWNER_NAME, SITUS_ADDR, OWNER_ADDR, OWNER_CITY, ZIPCODE,
YEAR_BUILT, LIVING_ARE, LAND_ACRES, IMPR_VALUE, TOTAL_VALU, DEED_DATE.

CAVEAT (STUBS JOB-002): LIVING_ARE is *residential* living area; commercial / barn /
church improvement SF is often null here and must come from the appraisal roll or
another field. So improvement_sf may be None for the exact target types — the 15,000 SF
criterion is deferred to enrichment, not applied in meets_buy_box. The land-use code
field is also not confirmed, so property_type classification is a no-op until SPIKE-000
resolves it (parcels still ingest; they just won't pass the buy box yet — fail-closed).
"""
from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import date

import httpx

from app.ingest.parcels import RawParcel

log = logging.getLogger("realtydog.cad.tarrant")

TAD_QUERY_URL = (
    "https://mapit.tarrantcounty.com/arcgis/rest/services/"
    "Dynamic/TADParcels/FeatureServer/0/query"
)
PAGE = 2000  # server MaxRecordCount is 10000; stay well under


def _classify(attrs: dict) -> str | None:
    # TODO(JOB-002 / SPIKE-000): map TAD land-use code -> canonical ELIGIBLE_TYPES once
    # the code field is confirmed from the FeatureServer field list. Until then, return
    # None so meets_buy_box stays False (fail-closed on unknown type).
    return None


def _to_float(v) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except (ValueError, TypeError):
        return None


def _to_int(v) -> int | None:
    f = _to_float(v)
    return int(f) if f is not None else None


def _to_date(ms) -> date | None:
    if not ms:
        return None
    try:
        return date.fromtimestamp(int(ms) / 1000)  # ArcGIS epoch millis
    except (ValueError, TypeError, OSError, OverflowError):
        return None


def map_feature(attrs: dict, geom: dict | None = None) -> RawParcel | None:
    account = attrs.get("ACCOUNT")
    if not account:
        return None  # no key -> skip, never fabricate
    lat = lon = None
    if geom:
        lon, lat = geom.get("x"), geom.get("y")
    return RawParcel(
        apn=str(account).strip(),
        county="Tarrant",
        owner_name=attrs.get("OWNER_NAME"),
        situs_address=attrs.get("SITUS_ADDR"),
        city=attrs.get("OWNER_CITY"),
        zip=attrs.get("ZIPCODE"),
        lat=_to_float(lat),
        lon=_to_float(lon),
        owner_mailing_address=attrs.get("OWNER_ADDR"),
        acres=_to_float(attrs.get("LAND_ACRES")),
        improvement_sf=_to_int(attrs.get("LIVING_ARE")),  # residential SF — see caveat
        property_type=_classify(attrs),
        year_built=_to_int(attrs.get("YEAR_BUILT")),
        assessed_value=_to_float(attrs.get("TOTAL_VALU")),
        last_sale_date=_to_date(attrs.get("DEED_DATE")),
        source="tad_arcgis",
    )


def fetch_tarrant_parcels(where: str = "LAND_ACRES >= 5", timeout: float = 30.0) -> Iterator[RawParcel]:
    """Paginate the TAD FeatureServer. The server-side WHERE trims to >=5 acres so we
    pull only the buy-box-relevant slice, not all ~600k parcels. Fail-open: logs and
    stops on any HTTP/parse error rather than raising into the scheduler.
    """
    offset = 0
    with httpx.Client(timeout=timeout) as client:
        while True:
            params = {
                "where": where,
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "json",
                "resultOffset": offset,
                "resultRecordCount": PAGE,
            }
            try:
                resp = client.get(TAD_QUERY_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:  # noqa: BLE001 - fail open, never crash the job
                log.warning("tarrant fetch failed at offset=%s: %s", offset, exc)
                return
            feats = data.get("features", [])
            if not feats:
                return
            for feat in feats:
                parcel = map_feature(feat.get("attributes", {}), feat.get("geometry"))
                if parcel:
                    yield parcel
            if len(feats) < PAGE or not data.get("exceededTransferLimit"):
                return
            offset += PAGE
