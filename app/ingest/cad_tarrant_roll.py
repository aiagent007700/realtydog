"""TAD appraisal-roll join (JOB-002b) — land-use classification via the State Use Code.

The delimited PropertyData export has a HEADER row with named columns (confirmed 2026-08-02
against the real file), so we parse by column NAME — robust to column order:
  RP (R/C/P/M) · Account_Num · Exemption_Code · State_Use_Code · GIS_Link
JOIN KEY is **GIS_Link ↔ the GIS layer's GISLINK** — the roll's Account_Num is a DIFFERENT
ID system from the GIS ACCOUNT (verified: church apn 40331792 = roll Account_Num 68136).
State_Use_Code holds TAD's SPTB category with a subcode, e.g. F1A (commercial), F2B
(industrial), E1 (rural improved), D2 (farm improvements), C1C (vacant → not a venue).
The fixed-length variant (no header) is also supported, parsed by position.

HONEST LIMITATION: the export has no commercial building square footage (only residential
Living_Area + Improvement_Value $), so the 15,000 SF criterion can't come from TAD data.

ACTIVATION: set TARRANT_ROLL_PATH to the downloaded PropertyData file. Empty until then.
"""
from __future__ import annotations

import itertools
import logging
from collections.abc import Iterable
from dataclasses import dataclass

from app.config import settings

log = logging.getLogger("realtydog.cad.tarrant.roll")

# --- Texas SPTB state category code -> canonical ELIGIBLE_TYPES (prefix match) ----------
_STATE_CODE_TYPE = {
    "F1": "commercial",
    "F2": "industrial",
    "E": "ranch_with_structure",
    "D2": "ranch_with_structure",
}
_EXEMPT_PREFIX = "X"

# Delimited-file column names (the header) we read. GIS_Link is the JOIN KEY — it ties to
# the GIS layer's GISLINK (the roll's Account_Num is a DIFFERENT ID system from GIS ACCOUNT).
_COL = {
    "rp": "RP",
    "account": "Account_Num",
    "state": "State_Use_Code",
    "exempt": "Exemption_Code",
    "gis_link": "GIS_Link",
}
# Fixed-length fallback positions: name -> (0-based start, length).
_FIELDS = {"rp": (0, 1), "account": (5, 8), "exemption": (191, 4), "state_use": (195, 2)}
_MIN_LINE_LEN = 197


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
    s = (s or "").strip()
    return str(int(s)) if s.isdigit() else s


def _norm_gislink(s: str | None) -> str:
    """The roll's GIS_Link / GIS layer's GISLINK — space-padded; strip + uppercase."""
    return (s or "").strip().upper()


@dataclass
class RollRecord:
    account: str
    state_code: str | None
    property_type: str | None
    tax_exempt: bool | None


def _record(rp: str | None, account: str | None, state: str | None, exemption: str | None) -> RollRecord | None:
    if (rp or "").strip().upper() not in ("R", "C"):
        return None  # real property only (skip Personal / Mineral)
    acct = _norm_account(account)
    if not acct:
        return None
    state = (state or "").strip() or None
    exemption = (exemption or "").strip()
    return RollRecord(acct, state, classify_state_code(state), bool(exemption) or is_exempt(state))


def _slice(line: str, key: str) -> str:
    start, length = _FIELDS[key]
    return line[start : start + length].strip()


def parse_roll_line(line: str) -> RollRecord | None:
    """Fixed-length (positional) single-record parse."""
    if len(line) < _MIN_LINE_LEN:
        return None
    return _record(_slice(line, "rp"), _slice(line, "account"), _slice(line, "state_use"), _slice(line, "exemption"))


def parse_roll(lines: Iterable[str]) -> dict[str, RollRecord]:
    """Parse the roll into {account: RollRecord}. Delimited files (with a header) are parsed
    by column name; fixed-length files by position."""
    it = iter(lines)
    try:
        first = next(it).rstrip("\r\n")
    except StopIteration:
        return {}

    if "|" in first:  # delimited, header row — key by GIS_Link (the real join key)
        cols = {name: i for i, name in enumerate(first.split("|"))}
        i_state, i_gis = cols.get(_COL["state"]), cols.get(_COL["gis_link"])
        if i_state is None or i_gis is None:
            log.warning("roll header missing State_Use_Code/GIS_Link; got %s...", first[:80])
            return {}
        i_rp, i_acct, i_exempt = cols.get(_COL["rp"]), cols.get(_COL["account"]), cols.get(_COL["exempt"])
        out: dict[str, RollRecord] = {}
        for line in it:
            f = line.rstrip("\r\n").split("|")
            if len(f) <= max(i_state, i_gis):
                continue

            def at(i):
                return f[i] if (i is not None and i < len(f)) else ""

            gis = _norm_gislink(at(i_gis))
            if not gis:
                continue  # no GIS key -> can't join
            rec = _record(at(i_rp), at(i_acct), at(i_state), at(i_exempt))
            if rec:
                out[gis] = rec
        return out

    # fixed-length fallback (no header, no GIS_Link position) — keyed by account (legacy).
    out = {}
    for line in itertools.chain([first], it):
        rec = parse_roll_line(line)
        if rec:
            out[rec.account] = rec
    return out


def load_tarrant_roll(timeout: float = 120.0) -> dict[str, RollRecord]:
    """Load the roll from TARRANT_ROLL_PATH (local file) or TARRANT_ROLL_URL. Fail-open."""
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
    """Overlay roll land-use onto a RawParcel in place: state-code property_type wins over the
    owner-name church heuristic; set land_use_code (raw code, for auditing) + tax_exempt. A
    church that is roll-exempt (state type None) keeps its type but gains tax_exempt=True.
    No-op when the parcel's GIS_Link isn't in the roll."""
    key = _norm_gislink(getattr(parcel, "gis_link", None))
    rec = roll.get(key) if key else None
    if not rec:
        return parcel
    if rec.property_type:
        parcel.property_type = rec.property_type
    if rec.state_code:
        parcel.land_use_code = rec.state_code
    if rec.tax_exempt is not None:
        parcel.tax_exempt = rec.tax_exempt
    return parcel
