"""JOB-002b tests: SPTB classification + fixed-length roll parsing + enrichment."""
from app.ingest.cad_tarrant_roll import (
    RollRecord,
    _norm_account,
    classify_state_code,
    enrich_from_roll,
    is_exempt,
    parse_roll,
    parse_roll_line,
)
from app.ingest.parcels import RawParcel, normalize


def _make_line(rp="C", account="12345", exemption="", state="F1") -> str:
    """Build a fixed-length PropertyData record with fields at their confirmed positions."""
    buf = [" "] * 200

    def put(start_1based: int, value: str, length: int) -> None:
        value = (value or "")[:length].ljust(length)
        for i, ch in enumerate(value):
            buf[start_1based - 1 + i] = ch

    put(1, rp, 1)
    put(6, account.rjust(8, "0"), 8)  # account is zero-padded in the file
    put(192, exemption, 4)
    put(196, state, 2)
    return "".join(buf)


def test_classify_state_code():
    assert classify_state_code("F1") == "commercial"
    assert classify_state_code("F2") == "industrial"
    assert classify_state_code("E") == "ranch_with_structure"
    assert classify_state_code("D2") == "ranch_with_structure"
    assert classify_state_code("D1") is None  # bare ag land, not a venue
    assert classify_state_code("A") is None
    assert classify_state_code(None) is None


def test_is_exempt():
    assert is_exempt("X") is True
    assert is_exempt("F1") is False
    assert is_exempt(None) is None


def test_norm_account_drops_leading_zeros():
    assert _norm_account("00012345") == "12345"
    assert _norm_account("12345") == "12345"
    assert _norm_account("  12345 ") == "12345"


def _make_delim(rp="C", account="00012345", exemption="", state="F1") -> str:
    # layout order: RP, Appraisal_Year, Account_Num, Record_Type, PIDN, Owner_Name,
    # Owner_Address, Owner_CityState, Owner_Zip, Situs_Address, Proert_Address, TAD_Map,
    # MAPSCO, Exemption_Code, State_Use_Code
    cols = [""] * 16
    cols[0], cols[2], cols[13], cols[14] = rp, account, exemption, state
    return "|".join(cols)


def test_parse_roll_line_commercial():
    rec = parse_roll_line(_make_line(rp="C", account="12345", state="F1"))
    assert rec is not None
    assert rec.account == "12345"  # normalized from 00012345
    assert rec.property_type == "commercial"


def test_parse_roll_line_delimited():
    rec = parse_roll_line(_make_delim(rp="C", account="00012345", state="F2"))
    assert rec is not None
    assert rec.account == "12345"
    assert rec.property_type == "industrial"


def test_parse_roll_skips_header_row():
    header = _make_delim(rp="RP", account="Account_Num", state="State_Use_Code")
    assert parse_roll_line(header) is None


def test_parse_roll_line_skips_personal_property():
    assert parse_roll_line(_make_line(rp="P", account="99", state="F1")) is None


def test_parse_roll_exemption_sets_tax_exempt():
    rec = parse_roll_line(_make_line(rp="C", account="55", exemption="EX", state="E"))
    assert rec.property_type == "ranch_with_structure"
    assert rec.tax_exempt is True


def test_parse_roll_builds_dict():
    lines = [_make_line(account="100", state="F1"), _make_line(account="200", state="A")]
    roll = parse_roll(lines)
    assert set(roll) == {"100", "200"}
    assert roll["100"].property_type == "commercial"
    assert roll["200"].property_type is None


def test_enrich_commercial_overrides_type():
    p = RawParcel(apn="00012345", county="Tarrant", acres=20, property_type=None)
    roll = {"12345": RollRecord("12345", "F1", "commercial", False)}
    enrich_from_roll(p, roll)  # apn 00012345 normalizes to 12345 -> match
    assert p.property_type == "commercial"
    assert p.land_use_code == "F1"
    assert normalize(p)["meets_buy_box"] is True


def test_enrich_church_kept_but_marked_exempt():
    p = RawParcel(apn="A2", county="Tarrant", acres=12, property_type="church")
    roll = {"A2": RollRecord("A2", "X", None, True)}
    enrich_from_roll(p, roll)
    assert p.property_type == "church"  # roll type None -> keep church
    assert p.tax_exempt is True


def test_enrich_noop_when_absent():
    p = RawParcel(apn="ZZ", county="Tarrant", acres=20, property_type="church")
    enrich_from_roll(p, {})
    assert p.property_type == "church"
    assert p.tax_exempt is None
