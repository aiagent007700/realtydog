"""Unit tests for the JOB-002 parcel core + the TAD field mapping. No DB/network."""
from app.ingest.cad_tarrant import map_feature
from app.ingest.parcels import (
    RawParcel,
    _is_absentee,
    _owner_type,
    meets_buy_box,
    normalize,
)


def test_owner_type():
    assert _owner_type("SMITH JOHN") == "person"
    assert _owner_type("FIRST BAPTIST CHURCH") == "entity"
    assert _owner_type("ACME HOLDINGS LLC") == "entity"
    assert _owner_type("ESTATE OF JANE DOE") == "estate"
    assert _owner_type(None) is None


def test_absentee():
    assert _is_absentee("123 MAIN ST", "999 FAR RD") is True
    assert _is_absentee("123 Main St", "123  MAIN   ST") is False  # normalized-equal
    assert _is_absentee(None, "x") is None  # can't verify -> unknown


def test_buy_box_fails_closed_on_missing_acreage():
    p = RawParcel(apn="1", county="Tarrant", property_type="commercial", acres=None)
    assert meets_buy_box(p) is False


def test_buy_box_requires_eligible_type():
    # Acreage fine but no resolved type -> not a candidate (fail closed).
    assert meets_buy_box(RawParcel(apn="1", county="Tarrant", property_type=None, acres=20)) is False


def test_buy_box_pass():
    p = RawParcel(apn="1", county="Tarrant", property_type="church", acres=12)
    assert meets_buy_box(p) is True


def test_buy_box_wrong_county():
    p = RawParcel(apn="1", county="Harris", property_type="church", acres=12)
    assert meets_buy_box(p) is False


def test_tad_map_feature():
    attrs = {
        "ACCOUNT": " 12345 ",
        "OWNER_NAME": "FIRST BAPTIST CHURCH",
        "SITUS_ADDR": "100 FARM RD",
        "OWNER_ADDR": "PO BOX 9",
        "OWNER_CITY": "AZLE",
        "ZIPCODE": "76020",
        "LAND_ACRES": "18.5",
        "LIVING_ARE": "",  # empty residential SF -> None (the caveat in action)
        "YEAR_BUILT": "1985",
        "TOTAL_VALU": "850000",
        "DEED_DATE": None,
    }
    rp = map_feature(attrs, {"x": -97.2, "y": 32.9})
    assert rp is not None
    assert rp.apn == "12345"  # trimmed
    assert rp.county == "Tarrant"
    assert rp.acres == 18.5
    assert rp.improvement_sf is None  # empty LIVING_ARE
    assert rp.lat == 32.9 and rp.lon == -97.2
    assert rp.assessed_value == 850000.0

    d = normalize(rp)
    assert d["owner_type"] == "entity"
    assert d["absentee"] is True  # PO BOX 9 != 100 FARM RD
    # property_type unresolved -> not in the buy box yet (fail closed, by design)
    assert d["meets_buy_box"] is False


def test_tad_map_feature_no_account():
    assert map_feature({"OWNER_NAME": "X"}, None) is None
