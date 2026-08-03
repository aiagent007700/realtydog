"""JOB-001 tests: tax-sale HTML parsing + monthly-URL extraction. (bs4-gated)"""
import pytest

from app.ingest.cad_tax_sale import parse_monthly_urls, parse_tax_sale_html

_TABLE_HTML = """
<html><body>
<table>
  <tr><th>CAUSE NUMBER</th><th>ACCOUNT NUMBER</th><th>STATUS</th></tr>
  <tr><td>D31592-22</td><td>02492601</td><td>For Sale</td></tr>
  <tr><td>D40258-24</td><td>00752649</td><td>Withdrawn</td></tr>
  <tr><td>D45128-24</td><td>00919314</td><td>For Sale</td></tr>
</table>
<table>
  <tr><th>SOMETHING</th><th>ELSE</th></tr>
  <tr><td>ignore</td><td>this</td></tr>
</table>
</body></html>
"""


def test_parse_tax_sale_html():
    pytest.importorskip("bs4")
    recs = parse_tax_sale_html(_TABLE_HTML)
    # 3 data rows from the tax-sale table; the second table is ignored (no ACCOUNT/STATUS)
    assert len(recs) == 3
    assert recs[0].account == "2492601"  # normalized (leading zeros stripped)
    assert recs[0].cause_number == "D31592-22"
    assert recs[0].status == "For Sale"
    assert recs[1].status == "Withdrawn"  # status preserved; filtering happens in fetch()


def test_parse_monthly_urls():
    pytest.importorskip("bs4")
    html = (
        '<a href="/en/constables/constable-3/delinquent-tax-sales/'
        'monthly-tax-sales-listings/august-4--2026.html">Aug</a>'
        '<a href="/en/some/other/page.html">nope</a>'
    )
    urls = parse_monthly_urls(html)
    assert urls == [
        "https://www.tarrantcountytx.gov/en/constables/constable-3/"
        "delinquent-tax-sales/monthly-tax-sales-listings/august-4--2026.html"
    ]
