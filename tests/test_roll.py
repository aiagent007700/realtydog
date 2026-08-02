"""JOB-002b tests: SPTB state-code classification + roll enrichment. No DB/network."""
from app.ingest.cad_tarrant_roll import (
    RollRecord,
    classify_state_code,
    enrich_from_roll,
    is_exempt,
    parse_roll,
)
from app.ingest.parcels import RawParcel, normalize


def test_classify_state_code():
    assert classify_state_code("F1") == "commercial"
    assert classify_state_code("F2") == "industrial"
    assert classify_state_code("E") == "ranch_with_structure"
    assert classify_state_code("D2") == "ranch_with_structure"
    assert classify_state_code("E5") == "ranch_with_structure"  # subcode -> first char
    assert classify_state_code("D1") is None  # bare ag land, not a venue
    assert classify_state_code("A") is None  # residential
    assert classify_state_code("") is None
    assert classify_state_code(None) is None


def test_is_exempt():
    assert is_exempt("X") is True
    assert is_exempt("XV") is True
    assert is_exempt("F1") is False
    assert is_exempt(None) is None


def test_enrich_commercial_overrides_type_and_sets_sf():
    p = RawParcel(apn="A1", county="Tarrant", acres=20, property_type=None)
    roll = {"A1": RollRecord("A1", "F1", 22000, "commercial", False)}
    enrich_from_roll(p, roll)
    assert p.property_type == "commercial"
    assert p.improvement_sf == 22000
    assert p.land_use_code == "F1"
    assert p.tax_exempt is False
    assert normalize(p)["meets_buy_box"] is True  # commercial on 20 acres in Tarrant


def test_enrich_church_kept_but_marked_exempt():
    # Church (from owner-name heuristic) that is roll-exempt (state type None): keep church,
    # gain tax_exempt=True.
    p = RawParcel(apn="A2", county="Tarrant", acres=12, property_type="church")
    roll = {"A2": RollRecord("A2", "X", None, None, True)}
    enrich_from_roll(p, roll)
    assert p.property_type == "church"
    assert p.tax_exempt is True


def test_enrich_noop_when_absent():
    p = RawParcel(apn="ZZ", county="Tarrant", acres=20, property_type="church")
    enrich_from_roll(p, {})  # empty (unconfirmed) roll
    assert p.property_type == "church"
    assert p.tax_exempt is None


def test_parse_roll_pipe_delimited():
    # Uses the provisional COL header names; verifies the parsing plumbing.
    lines = [
        "Account_Num|State_Use_Code|Other",
        "12345|F1|x",
        "67890|A|y",
        "|F2|z",  # no account -> skipped
    ]
    roll = parse_roll(lines)
    assert set(roll) == {"12345", "67890"}
    assert roll["12345"].property_type == "commercial"
    assert roll["67890"].property_type is None
