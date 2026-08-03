"""SEL-002 — motivation score (Layer 2). Ranks buy-box parcels by likelihood-to-sell.

Score = sum of applicable signal weights (README §8), an explainable point-sum (never a
black box). Owner-attribute signals come from `parcels`; distress signals from
`distress_signals` (populated by JOB-001/003/004/008). Until those distress jobs run, only
owner attributes contribute — so the score still ranks the list, it just can't reach the
top tier on distress yet. Buckets: Hot ≥60 / Warm 30–59 / Cold <30 (config thresholds).

Writes `motivation_score` + `score_breakdown` (the *why*) to one `prospects` row per
buy-box parcel, leaving user-managed status/assigned_to/notes untouched.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Iterable

from sqlalchemy import text

from app.config import settings
from app.db import engine

log = logging.getLogger("realtydog.score.motivation")

# Signal weights (README §8). Distress-signal keys match `distress_signals.signal_type`.
_WEIGHTS = {
    "tax_sale": 40,
    "tax_delinquent": 40,
    "nonprofit_distress": 35,
    "foreclosure_posting": 35,
    "probate": 25,
    "lis_pendens": 20,
    "code_violation": 15,
    # owner-attribute signals (derived, not from distress_signals)
    "estate_owner": 25,
    "absentee": 15,
    "out_of_state": 10,
    "long_tenure": 10,
}
_LONG_TENURE_YEARS = 20


def bucket(score: int) -> str:
    if score >= settings.motivation_hot:
        return "hot"
    if score >= settings.motivation_warm:
        return "warm"
    return "cold"


def score_prospect(
    *,
    absentee: bool | None,
    out_of_state: bool,
    tenure_years: int | None,
    owner_type: str | None,
    signal_types: Iterable[str] | None,
) -> tuple[int, dict]:
    """Pure, explainable score. Returns (total, breakdown) where breakdown maps each
    contributing signal to its points — always stored so the score is auditable."""
    breakdown: dict[str, int] = {}
    for st in set(signal_types or []):
        if st in _WEIGHTS:
            breakdown[st] = _WEIGHTS[st]
    # Don't double-count an estate owner if a probate distress signal already fired.
    if owner_type == "estate" and "probate" not in breakdown:
        breakdown["estate_owner"] = _WEIGHTS["estate_owner"]
    if absentee:
        breakdown["absentee"] = _WEIGHTS["absentee"]
    if out_of_state:
        breakdown["out_of_state"] = _WEIGHTS["out_of_state"]
    if tenure_years is not None and tenure_years >= _LONG_TENURE_YEARS:
        breakdown["long_tenure"] = _WEIGHTS["long_tenure"]
    return sum(breakdown.values()), breakdown


_SELECT = text(
    """
    SELECT p.id, p.absentee, p.tenure_years, p.owner_type, p.owner_mailing_state,
           COALESCE(array_agg(ds.signal_type) FILTER (WHERE ds.signal_type IS NOT NULL),
                    ARRAY[]::text[]) AS signals
    FROM parcels p
    LEFT JOIN distress_signals ds ON ds.parcel_id = p.id
    WHERE p.meets_buy_box
    GROUP BY p.id
    """
)

_UPSERT = text(
    """
    INSERT INTO prospects (parcel_id, motivation_score, score_breakdown, updated_at)
    VALUES (:parcel_id, :score, CAST(:breakdown AS jsonb), now())
    ON CONFLICT (parcel_id) DO UPDATE SET
      motivation_score = EXCLUDED.motivation_score,
      score_breakdown = EXCLUDED.score_breakdown,
      updated_at = now()
    """
)


def run_motivation_scoring() -> int:
    """Score every buy-box parcel and upsert into `prospects`. Returns rows scored."""
    scored = 0
    with engine.begin() as conn:
        for row in conn.execute(_SELECT).fetchall():
            out_of_state = (row.owner_mailing_state or "").strip().upper() not in ("", "TX")
            total, breakdown = score_prospect(
                absentee=row.absentee,
                out_of_state=out_of_state,
                tenure_years=row.tenure_years,
                owner_type=row.owner_type,
                signal_types=row.signals,
            )
            conn.execute(
                _UPSERT,
                {"parcel_id": row.id, "score": total, "breakdown": json.dumps(breakdown)},
            )
            scored += 1
    log.info("motivation scoring: %d prospects scored", scored)
    return scored


if __name__ == "__main__":  # `python -m app.score.motivation`
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(f"motivation scoring: {run_motivation_scoring()} prospects updated")
