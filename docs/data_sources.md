# Data Sources — SPIKE-000 findings (Job 0)

Desk research verifying what the tax-sale firms and the four core county appraisal
districts actually publish, **before** JOB-001/JOB-002 are built against them. Status per
source is **verified** (confirmed from the source/portal) or **to verify** (needs
interactive inspection or a field-reference doc during the build).

_Last researched: 2026-08-02._

---

## Tax-sale lists (feeds JOB-001)

Texas tax sales are run by law firms per taxing entity; the DFW core splits across three,
with the county constable/courthouse as a fallback. Sales are **monthly** (first Tuesday);
lists + minimum bids post around the **15th of the prior month**.

| Firm | Portal | Core DFW counties | Format | Notes |
|------|--------|-------------------|--------|-------|
| **Linebarger (LGBS)** | `taxsales.lgbs.com` | **Dallas, Tarrant** | Dynamic web portal; filter Sale Date / County / Sale Type → downloadable "County Property Sale List" | **JS single-page app** — a static HTML fetch returns only the shell. Build must call its backend data endpoint or pull the per-sale list file. No documented public JSON API. |
| **MVBA** | `mvbalaw.com/tax-sales` | **Collin, Denton** (+100 counties) | Bid sheets posted on site + mailed to subscribers; monthly directory | Per-county bid sheets. |
| **Perdue Brandon** | `pbfcm.com` | Various TX counties | Per-county tax-foreclosure lists | Confirm DFW coverage vs MVBA. |
| County fallback | Constable / county sites | per county | HTML (Tarrant Constable monthly listings; Denton "Delinquent Tax Sales"; Collin "Properties for Sale") | Lists account/cause numbers; address resolved via the CAD. |

**Confirmed gotchas:**
- Tax-sale rows are keyed by **account number + cause number + legal description**, not
  clean street addresses — Tarrant explicitly says to resolve the address via TAD. So
  match to `parcels` by **APN/account + legal description**, not address (confirms the
  STUBS/README note).
- **No unified API** across firms — JOB-001 is one small adapter per firm, monthly cadence.
- The LGBS list drops ~the **15th** — the weekly poll must be timed to catch it.

---

## County appraisal data (feeds JOB-002 — the parcel universe)

All four core counties publish appraisal data **for free**. Importantly, **two expose
real open-data APIs**, which are cleaner than parsing bulk ZIPs.

| County | Source | Access | Format | Status |
|--------|--------|--------|--------|--------|
| **Dallas (DCAD)** | `dallascad.org/dataproducts.aspx` | Bulk download | ZIP of comma-delimited + fixed-format files; field-reference docs included | ✅ verified (bulk only, no API) |
| **Tarrant (TAD)** | `gis-tad.opendata.arcgis.com` | **ArcGIS Hub API** + download | CSV / GeoJSON / KML / Zip; ArcGIS REST | ✅ verified (API available) |
| **Collin (CollinCAD)** | `collincad.org/open-data-portal` + `data.texas.gov` | **Socrata API** + exports | CSV/Excel via Socrata (SODA API); code-description spreadsheets; GIS shapefiles | ✅ verified (API available) |
| **Denton (DentonCAD)** | `denton.prodigycad.com/data-downloads`; `gis.dentoncad.com`; `data-dentoncounty.hub.arcgis.com` | Downloads + ArcGIS parcels | Downloadable files + ArcGIS; fields documented in `DCAD_Schema.pdf` | ✅ verified (downloads + GIS; confirm the tabular appraisal export) |

**Architectural conclusion:** prefer the **open-data API** path (Tarrant ArcGIS, Collin
Socrata, Denton ArcGIS) over screen-scraping; use **DCAD's bulk ZIP** for Dallas. JOB-002
is therefore a small set of API clients + one ZIP loader — **not a scraper**.

---

## Still to verify during the build (field-level)

Desk research confirms **availability and format**; it does not yet confirm every field
we need is present. Before JOB-002 is "done," confirm each county's export contains:

- **Owner mailing address** (required for mail-first) — the DCAD / CollinCAD / TAD rolls
  include it; confirm in each field-reference doc / schema (e.g. Denton `DCAD_Schema.pdf`).
- **Acreage / land size**, **improvement SF**, **land-use code**, and the
  **exemption / tax-exempt flag** (the last feeds JOB-008 non-profit detection).

Grab each county's field-reference doc first, then map its columns to the `parcels` schema.

---

## Gates this resolves / opens

- **Resolves** the "is CAD data even reachable?" risk — yes, free, for all four counties,
  with two of them API-first.
- **Still open (decision #1):** which 2–3 counties are primary. **Recommendation from this
  research: start with Dallas + Tarrant** — LGBS covers both on the tax-sale side, DCAD
  bulk + TAD API are both confirmed free, and they're the two largest markets. Add Collin
  (clean Socrata API) third.

---

## Sources

- [LGBS tax-sale portal](https://taxsales.lgbs.com/)
- [Dallas County tax office FAQ](https://www.dallascounty.org/departments/tax/other-questions.php)
- [Tarrant Constable delinquent tax sales](https://www.tarrantcountytx.gov/en/constables/constable-3/delinquent-tax-sales.html)
- [MVBA tax sales](https://mvbalaw.com/tax-sales/)
- [Collin County properties for sale](https://www.collincountytx.gov/Tax-Assessor/properties-for-sale)
- [Denton County delinquent tax sales](https://www.dentoncounty.gov/867/Delinquent-Tax-Sales)
- [DCAD data products](https://www.dallascad.org/dataproducts.aspx)
- [Tarrant Appraisal District open data](https://gis-tad.opendata.arcgis.com/)
- [Collin CAD open data portal](https://collincad.org/open-data-portal/)
- [Collin CAD appraisal data on data.texas.gov](https://data.texas.gov/dataset/Collin-CAD-Appraisal-Data-2025/vffy-snc6)
- [Denton CAD data downloads](https://denton.prodigycad.com/data-downloads)
- [Denton CAD GIS schema PDF](https://www.dentoncad.com/data/_uploaded/GISPub/DCAD_Schema.pdf)
