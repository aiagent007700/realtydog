"""Parcel normalization + Layer-1 physical buy-box (README §2).

Pure functions — no I/O — so they are unit-testable without a DB or network.
County adapters (cad_tarrant, cad_dallas) produce a RawParcel; normalize() turns
one into a dict ready for upsert into `parcels`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from app.config import settings

# Land-use buckets we treat as event-venue-convertible. Source land-use codes vary
# by county, so each adapter classifies into these canonical types; unknown -> None.
ELIGIBLE_TYPES = {
    "barn",
    "church",
    "commercial",
    "warehouse",
    "ranch_with_structure",
    "mixed_use",
    "industrial",
}


@dataclass
class RawParcel:
    apn: str
    county: str
    owner_name: str | None = None
    situs_address: str | None = None
    city: str | None = None
    zip: str | None = None
    lat: float | None = None
    lon: float | None = None
    owner_mailing_address: str | None = None
    owner_mailing_state: str | None = None
    acres: float | None = None
    improvement_sf: int | None = None
    land_use_code: str | None = None
    property_type: str | None = None  # canonical (ELIGIBLE_TYPES), set by the adapter
    year_built: int | None = None
    assessed_value: float | None = None
    last_sale_date: date | None = None
    tax_exempt: bool | None = None  # from the appraisal-roll state code (X = exempt)
    source: str | None = None


def _norm(s: str) -> str:
    return " ".join(s.upper().split())


def _owner_type(owner_name: str | None) -> str | None:
    if not owner_name:
        return None
    n = f" {owner_name.upper()} "
    if "ESTATE OF" in n or " ESTATE " in n:
        return "estate"
    markers = (" LLC", " INC", " CORP", " LP ", " LTD", " TRUST", " CHURCH",
               " MINISTR", " FOUNDATION", " ASSN", " ASSOCIATION")
    if any(m in n for m in markers):
        return "entity"
    return "person"


def _is_absentee(situs: str | None, mailing: str | None) -> bool | None:
    if not situs or not mailing:
        return None  # can't verify -> unknown, not "False"
    return _norm(situs) != _norm(mailing)


def _tenure_years(last_sale: date | None) -> int | None:
    if not last_sale:
        return None
    return max(0, (datetime.now(UTC).date() - last_sale).days // 365)


def meets_buy_box(p: RawParcel) -> bool:
    """Layer-1 PHYSICAL universe filter. Geography + acreage + eligible type must be
    verifiable (fail closed on missing). The 15,000 SF check is deliberately NOT applied
    here: county sources reliably carry residential living area but often not commercial
    improvement SF, so SF is confirmed later at enrichment/analysis (see STUBS JOB-002).
    Purchase price / the $5M all-in are the Layer-3 gate, not this filter.
    """
    if p.county not in settings.counties:
        return False
    if p.acres is None or p.acres < settings.buybox_min_acres:
        return False  # unverifiable / too-small acreage -> fail closed
    if p.property_type not in ELIGIBLE_TYPES:
        return False  # unknown or ineligible type -> not a candidate
    return True


def normalize(p: RawParcel) -> dict:
    return {
        "apn": p.apn,
        "county": p.county,
        "situs_address": p.situs_address,
        "city": p.city,
        "zip": p.zip,
        "lat": p.lat,
        "lon": p.lon,
        "owner_name": p.owner_name,
        "owner_type": _owner_type(p.owner_name),
        "owner_mailing_address": p.owner_mailing_address,
        "owner_mailing_state": p.owner_mailing_state,
        "acres": p.acres,
        "improvement_sf": p.improvement_sf,
        "land_use_code": p.land_use_code,
        "year_built": p.year_built,
        "assessed_value": p.assessed_value,
        "last_sale_date": p.last_sale_date,
        "tax_exempt": p.tax_exempt,
        "absentee": _is_absentee(p.situs_address, p.owner_mailing_address),
        "tenure_years": _tenure_years(p.last_sale_date),
        "meets_buy_box": meets_buy_box(p),
        "source": p.source,
    }
