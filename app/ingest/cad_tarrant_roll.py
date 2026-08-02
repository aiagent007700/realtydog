"""TAD appraisal-roll join (JOB-002b) — land-use classification + commercial SF.

The TADParcels GIS layer has no land-use code (verified — see cad_tarrant.py). The Texas
state category (SPTB) code and real improvement SF live in TAD's **PropertyData** export
(pipe-delimited "AAAA" layout; PropertyData-FullSet / -Commercial), joined to the GIS
layer by ACCOUNT (a.k.a. TAXPIN). This module loads that roll and enriches each parcel.

WHAT IS VERIFIED/KNOWN (encoded here):
  - Format: pipe-delimited PropertyData export (tad.org/resources/data-downloads).
  - Join key: ACCOUNT / TAXPIN (present in both the roll and the GIS layer).
  - The Texas SPTB state-category-code -> property-type mapping (standard statewide).

WHAT IS NOT YET VERIFIED (isolated behind COLUMNS_CONFIRMED):
  - The exact PropertyData column names/positions for account, state code, and improvement
    SF. The layout doc (PropertyData&PropertyLocationLayouts.pdf) blocks automated fetch —
    confirm it manually (open the PDF, or read the delimited file's header), fill COL, set
    the download URL, and flip COLUMNS_CONFIRMED. Until then load_tarrant_roll() returns {}
    (logged), so wiring it in is harmless (behaviour = church-only classification).
"""
from __future__ import annotations

import csv
import logging
from collections.abc import Iterable
from dataclasses import dataclass

log = logging.getLogger("realtydog.cad.tarrant.roll")

# --- Verified: Texas SPTB state category code -> canonical ELIGIBLE_TYPES ---------------
# F1 commercial real, F2 industrial real, E rural land w/ improvements, D2 farm/ranch
# improvements (barns). D1 (bare ag land) and A/B/C (residential/vacant) are NOT venues.
_STATE_CODE_TYPE = {
    "F1": "commercial",
    "F2": "industrial",
    "E": "ranch_with_structure",
    "D2": "ranch_with_structure",
}
_EXEMPT_PREFIX = "X"  # SPTB X = totally exempt (churches, government, charities)


def classify_state_code(code: str | None) -> str | None:
    """Map an SPTB state category code to a canonical property_type, or None."""
    if not code:
        return None
    c = code.strip().upper()
    return _STATE_CODE_TYPE.get(c) or _STATE_CODE_TYPE.get(c[:2]) or _STATE_CODE_TYPE.get(c[:1])


def is_exempt(code: str | None) -> bool | None:
    if not code:
        return None
    return code.strip().upper().startswith(_EXEMPT_PREFIX)


# --- NOT verified: PropertyData column layout (confirm from the doc, then flip) ---------
COLUMNS_CONFIRMED = False
ROLL_URL = ""  # e.g. the PropertyData-Commercial (Delimited) download URL
COL = {
    # header name (or index) in the pipe-delimited PropertyData file — CONFIRM from
    # https://www.tad.org/content/forms/PropertyData&PropertyLocationLayouts.pdf
    "account": "Account_Num",
    "state_code": "State_Use_Code",
    "improvement_sf": None,  # confirm the building/improvement-SF column name
}


@dataclass
class RollRecord:
    account: str
    state_code: str | None
    improvement_sf: int | None
    property_type: str | None
    tax_exempt: bool | None


def _to_int(v) -> int | None:
    try:
        return int(float(v)) if v not in (None, "") else None
    except (ValueError, TypeError):
        return None


def parse_roll_row(row: dict) -> RollRecord | None:
    """Build a RollRecord from one parsed pipe-delimited row (header -> value)."""
    account = (row.get(COL["account"]) or "").strip()
    if not account:
        return None
    state_code = row.get(COL["state_code"])
    sf = _to_int(row.get(COL["improvement_sf"])) if COL["improvement_sf"] else None
    return RollRecord(
        account=account,
        state_code=state_code,
        improvement_sf=sf,
        property_type=classify_state_code(state_code),
        tax_exempt=is_exempt(state_code),
    )


def parse_roll(lines: Iterable[str]) -> dict[str, RollRecord]:
    """Parse pipe-delimited PropertyData lines (with a header row) into {account: record}."""
    reader = csv.DictReader(lines, delimiter="|")
    out: dict[str, RollRecord] = {}
    for row in reader:
        rec = parse_roll_row(row)
        if rec:
            out[rec.account] = rec
    return out


def load_tarrant_roll(timeout: float = 120.0) -> dict[str, RollRecord]:
    """Download + parse the PropertyData roll. Gated on COLUMNS_CONFIRMED; fail-open."""
    if not COLUMNS_CONFIRMED or not ROLL_URL:
        log.info("TAD roll pending column confirmation (JOB-002b) — returning empty join")
        return {}
    import httpx

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(ROLL_URL)
            resp.raise_for_status()
            return parse_roll(resp.text.splitlines())
    except Exception as exc:  # noqa: BLE001 - fail open, never crash the job
        log.warning("TAD roll load failed: %s", exc)
        return {}


def enrich_from_roll(parcel, roll: dict[str, RollRecord]):
    """Overlay roll data onto a RawParcel in place: state-code property_type (wins over the
    owner-name church heuristic), real improvement SF, land_use_code, and tax_exempt. A
    church parcel that is roll-exempt (state type None) keeps its church type but gains
    tax_exempt=True. No-op when the account isn't in the roll (e.g. empty roll)."""
    rec = roll.get(parcel.apn)
    if not rec:
        return parcel
    if rec.property_type:
        parcel.property_type = rec.property_type
    if rec.improvement_sf is not None:
        parcel.improvement_sf = rec.improvement_sf
    if rec.state_code:
        parcel.land_use_code = rec.state_code
    if rec.tax_exempt is not None:
        parcel.tax_exempt = rec.tax_exempt
    return parcel
