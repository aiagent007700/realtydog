"""JOB-001 — Tarrant tax-sale distress signals from the County Constable Pct-3 monthly lists.

Source: tarrantcountytx.gov constable-3 monthly tax-sale pages (accessible — NOT behind TAD's
Cloudflare block). Each monthly page has HTML tables with columns CAUSE NUMBER / ACCOUNT
NUMBER / STATUS. Active ("For Sale") accounts are matched to `parcels.apn` (normalized) and
written as `distress_signals(signal_type='tax_sale')` — which SEL-002 weights +40, so a
tax-delinquent parcel jumps toward Hot.

Reality check: most tax-delinquent properties are small residential, so matches against our
5+ acre parcel universe will be SPARSE. But each match is a genuine distress signal, and the
machinery works for every future (commercial) parcel too.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from sqlalchemy import text

from app.db import engine
from app.ingest.cad_tarrant_roll import _norm_account

log = logging.getLogger("realtydog.ingest.tax_sale")

_INDEX_URL = (
    "https://www.tarrantcountytx.gov/en/constables/constable-3/"
    "delinquent-tax-sales/monthly-tax-sales-listings.html"
)
_BASE = "https://www.tarrantcountytx.gov"
_ACTIVE = "for sale"
_SOURCE = "tarrant_constable"


@dataclass
class TaxSaleRecord:
    account: str  # normalized (leading zeros stripped)
    cause_number: str | None
    status: str


def parse_tax_sale_html(html: str) -> list[TaxSaleRecord]:
    """Parse every table that has ACCOUNT NUMBER + STATUS columns."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    out: list[TaxSaleRecord] = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header = [c.get_text(strip=True).upper() for c in rows[0].find_all(["th", "td"])]
        if "ACCOUNT NUMBER" not in header or "STATUS" not in header:
            continue
        i_acct = header.index("ACCOUNT NUMBER")
        i_stat = header.index("STATUS")
        i_cause = header.index("CAUSE NUMBER") if "CAUSE NUMBER" in header else None
        for row in rows[1:]:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) <= max(i_acct, i_stat):
                continue
            account = _norm_account(cells[i_acct])
            if not account:
                continue
            cause = cells[i_cause] if (i_cause is not None and i_cause < len(cells)) else None
            out.append(TaxSaleRecord(account=account, cause_number=cause, status=cells[i_stat]))
    return out


def parse_monthly_urls(html: str) -> list[str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    urls = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "monthly-tax-sales-listings/" in href and href.endswith(".html"):
            urls.add(href if href.startswith("http") else _BASE + href)
    return sorted(urls)


def fetch_tarrant_tax_sales(timeout: float = 30.0) -> list[TaxSaleRecord]:
    """Fetch the index, then each monthly page; return the active ('For Sale') records.
    Fail-open: logs and returns whatever it got on any error."""
    import httpx

    active: list[TaxSaleRecord] = []
    try:
        with httpx.Client(timeout=timeout, headers={"User-Agent": "RealtyDog/0.1"}) as client:
            idx = client.get(_INDEX_URL)
            idx.raise_for_status()
            for url in parse_monthly_urls(idx.text):
                try:
                    page = client.get(url)
                    page.raise_for_status()
                    for rec in parse_tax_sale_html(page.text):
                        if rec.status.strip().lower() == _ACTIVE:
                            active.append(rec)
                except Exception as exc:  # noqa: BLE001
                    log.warning("tax-sale page failed (%s): %s", url, exc)
    except Exception as exc:  # noqa: BLE001 - fail open
        log.warning("tax-sale index fetch failed: %s", exc)
    return active


_PARCEL_IDX = text("SELECT id, apn FROM parcels")
_DELETE = text("DELETE FROM distress_signals WHERE source = :src")
_INSERT = text(
    """
    INSERT INTO distress_signals (parcel_id, signal_type, source, cause_number, raw, ingested_at)
    VALUES (:pid, 'tax_sale', :src, :cause, CAST(:raw AS jsonb), now())
    """
)


def run_tax_sale_ingest() -> tuple[int, int]:
    """Fetch active tax sales, match to parcels, refresh this source's distress_signals.
    Returns (n_active_listings, n_matched_to_parcels)."""
    records = fetch_tarrant_tax_sales()
    if not records:
        # Don't wipe existing signals on a transient fetch failure / empty result.
        log.warning("tax-sale ingest: no active records — keeping existing signals")
        return 0, 0
    matched = 0
    with engine.begin() as conn:
        index = {_norm_account(apn): pid for pid, apn in conn.execute(_PARCEL_IDX).fetchall()}
        conn.execute(_DELETE, {"src": _SOURCE})  # refresh: reflect the current listings
        for rec in records:
            pid = index.get(rec.account)
            if pid is None:
                continue  # not one of our parcels (most tax-sale rows won't be)
            conn.execute(
                _INSERT,
                {
                    "pid": pid,
                    "src": _SOURCE,
                    "cause": rec.cause_number,
                    "raw": json.dumps({"account": rec.account, "status": rec.status,
                                       "cause_number": rec.cause_number}),
                },
            )
            matched += 1
    log.info("tax-sale ingest: %d active listings, %d matched to parcels", len(records), matched)
    return len(records), matched


if __name__ == "__main__":  # `python -m app.ingest.cad_tax_sale`
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    n, m = run_tax_sale_ingest()
    print(f"tax-sale ingest: {n} active listings, {m} matched to your parcels")
