"""TAD appraisal-roll join (JOB-002b) — land-use classification via the State Use Code.

Layout CONFIRMED 2026-08-02 from TAD's PropertyData "AAAA" **fixed-length** layout. Fields
we use (1-based Pos / Len):
  RP              1/1    account type: R residential, C commercial, P personal, M mineral
  Account_Num     6/8    join key (== the GIS layer's ACCOUNT, normalized)
  Exemption_Code  192/4  non-blank => some exemption (feeds tax_exempt / JOB-008)
  State_Use_Code  196/2  Texas SPTB category (F1 commercial, F2 industrial, E/D2 ranch...)

HONEST LIMITATION: the export has **no commercial building square footage** — only
`Living_Area` (residential) and `Improvement_Value` ($). So the 15,000 SF criterion cannot
be sourced from TAD free data; this join delivers property_type + exempt flag, not SF.

ACTIVATION: download the fixed-length PropertyData FullSet from tad.org/resources/data-downloads,
save it locally, and set `TARRANT_ROLL_PATH` in .env to that file. `load_tarrant_roll()`
returns `{}` until then (church-only classification, no behaviour change).
"""
from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass

from app.config import settings

log = logging.getLogger("realtydog.cad.tarrant.roll")

# --- Verified: Texas SPTB state category code -> canonical ELIGIBLE_TYPES ---------------
_STATE_CODE_TYPE = {
    "F1": "commercial",
    "F2": "industrial",
    "E": "ranch_with_structure",
    "D2": "ranch_with_structure",
}
_EXEMPT_PREFIX = "X"

# --- Confirmed fixed-length field positions: name -> (0-based start, length) ------------
_FIELDS = {
    "rp": (0, 1),
    "account": (5, 8),
    "exemption": (191, 4),
    "state_use": (195, 2),
}
_MIN_LINE_LEN = 197  # must reach the State_Use_Code field


def classify_state_code(code: str | None) -> str | None:
    if not code:
        return None
    c = code.strip().upper()
    return _STATE_CODE_TYPE.get(c) or _STATE_CODE_TYPE.get(c[:2]) or _STATE_CODE_TYPE.get(c[:1])


def is_exempt(code: str | None) -> bool | None:
    if not code:
        return None
    return code.strip().upper().startswith(_EXEMPT_PREFIX)


def _norm_account(s: str | None) -> str:
    """Normalize an account number for joining (strip; drop leading zeros if numeric)."""
    s = (s or "").strip()
    return str(int(s)) if s.isdigit() else s


def _slice(line: str, key: str) -> str:
    start, length = _FIELDS[key]
    return line[start : start + length].strip()


@dataclass
class RollRecord:
    account: str
    state_code: str | None
    property_type: str | None
    tax_exempt: bool | None


def parse_roll_line(line: str) -> RollRecord | None:
    if len(line) < _MIN_LINE_LEN:
        return None
    if _slice(line, "rp").upper() not in ("R", "C"):
        return None  # real property only (skip Personal / Mineral)
    account = _norm_account(_slice(line, "account"))
    if not account:
        return None
    state = _slice(line, "state_use") or None
    exemption = _slice(line, "exemption")
    return RollRecord(
        account=account,
        state_code=state,
        property_type=classify_state_code(state),
        tax_exempt=bool(exemption) or is_exempt(state),
    )


def parse_roll(lines: Iterable[str]) -> dict[str, RollRecord]:
    out: dict[str, RollRecord] = {}
    for line in lines:
        rec = parse_roll_line(line)
        if rec:
            out[rec.account] = rec
    return out


def load_tarrant_roll(timeout: float = 120.0) -> dict[str, RollRecord]:
    """Load the fixed-length PropertyData roll from TARRANT_ROLL_PATH (local file), or a
    URL if configured. Fail-open: any error -> empty join (church-only classification)."""
    path = getattr(settings, "tarrant_roll_path", "")
    if path:
        try:
            with open(path, encoding="latin-1", errors="replace") as fh:
                return parse_roll(fh)
        except OSError as exc:
            log.warning("TAD roll file read failed (%s): %s", path, exc)
            return {}
    url = getattr(settings, "tarrant_roll_url", "")
    if url:
        import httpx

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(url)
                resp.raise_for_status()
                return parse_roll(resp.text.splitlines())
        except Exception as exc:  # noqa: BLE001 - fail open
            log.warning("TAD roll download failed: %s", exc)
            return {}
    log.info("TAD roll not configured (set TARRANT_ROLL_PATH) — empty join, church-only classify")
    return {}


def enrich_from_roll(parcel, roll: dict[str, RollRecord]):
    """Overlay roll land-use onto a RawParcel in place: state-code property_type wins over
    the owner-name church heuristic; set land_use_code + tax_exempt. A church that is
    roll-exempt (state type None) keeps its type but gains tax_exempt=True. No SF (the roll
    has no commercial SF). No-op when the account isn't in the roll (e.g. empty roll)."""
    rec = roll.get(_norm_account(parcel.apn))
    if not rec:
        return parcel
    if rec.property_type:
        parcel.property_type = rec.property_type
    if rec.state_code:
        parcel.land_use_code = rec.state_code
    if rec.tax_exempt is not None:
        parcel.tax_exempt = rec.tax_exempt
    return parcel
