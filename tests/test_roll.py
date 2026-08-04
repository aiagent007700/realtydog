"""JOB-002b tests: SPTB classification + delimited roll parse (keyed by GIS_Link) + enrichment."""
from app.ingest.cad_tarrant_roll import (
    RollRecord,
    _norm_account,
    _norm_gislink,
    classify_state_code,
    enrich_from_roll,
    is_exempt,
    parse_roll,
    parse_roll_line,
)
from app.ingest.parcels import RawParcel, normalize


def _make_line(rp="C", account="12345", exemption="", state="F1") -> str:
    """Fixed-length record (RP@1, Account_Num@6, Exemption_Code@192, State_Use_Code@196)."""
    buf = [" "] * 200

    def put(start_1based, value, length):
        value = (value or "")[:length].ljust(length)
        for i, ch in enumerate(value):
            buf[start_1based - 1 + i] = ch

    put(1, rp, 1)
    put(6, account.rjust(8, "0"), 8)
    put(192, exemption, 4)
    put(196, state, 2)
    return "".join(buf)


# Real delimited header (subset through GIS_Link) — parse keys off the names.
_DELIM_HEADER = (
    "RP|Appraisal_Year|Account_Num|Record_Type|Sequence_No|PIDN|Owner_Name|Owner_Address|"
    "Owner_CityState|Owner_Zip|Owner_Zip4|Owner_CRRT|Situs_Address|Property_Class|TAD_Map|"
    "MAPSCO|Exemption_Code|State_Use_Code|LegalDescription|GIS_Link"
)


def _delim_row(rp="C", account="00012345", exemption="", state="F1A", gislink="13740-1-1AR1R1") -> str:
    cols = [""] * 20
    cols[0], cols[2], cols[16], cols[17], cols[19] = rp, account, exemption, state, gislink
    return "|".join(cols)


def test_classify_state_code():
    assert classify_state_code("F1") == "commercial"
    assert classify_state_code("F1A") == "commercial"  # SPTB subcode
    assert classify_state_code("F2B") == "industrial"
    assert classify_state_code("E") == "ranch_with_structure"
    assert classify_state_code("D2") == "ranch_with_structure"
    assert classify_state_code("C1C") is None  # vacant lot -> not a venue
    assert classify_state_code("A") is None  # residential
    assert classify_state_code(None) is None


def test_is_exempt():
    assert is_exempt("X") is True
    assert is_exempt("F1") is False
    assert is_exempt(None) is None


def test_norm_helpers():
    assert _norm_account("00068136") == "68136"
    assert _norm_gislink("13740-1-1AR1R1    ") == "13740-1-1AR1R1"  # strips padding


def test_parse_roll_line_fixed_width():
    rec = parse_roll_line(_make_line(rp="C", account="12345", state="F1"))
    assert rec is not None and rec.property_type == "commercial"


def test_parse_roll_delimited_keyed_by_gislink():
    lines = [
        _DELIM_HEADER,
        _delim_row(state="F1A", gislink="13740-1-1AR1R1"),  # commercial
        _delim_row(account="200", state="F2B", gislink="910-18-9"),  # industrial
        _delim_row(account="300", state="C1C", gislink="55-1-1"),  # vacant -> None
        _delim_row(account="400", state="F1", gislink=""),  # no GIS key -> skipped
        _delim_row(rp="P", state="F1", gislink="99-9-9"),  # personal property -> skipped
    ]
    roll = parse_roll(lines)
    assert set(roll) == {"13740-1-1AR1R1", "910-18-9", "55-1-1"}  # keyed by GIS_Link
    assert roll["13740-1-1AR1R1"].property_type == "commercial"
    assert roll["910-18-9"].property_type == "industrial"
    assert roll["55-1-1"].property_type is None


def test_enrich_commercial_overrides_type():
    p = RawParcel(apn="40331792", county="Tarrant", acres=20, property_type=None)
    p.gis_link = "13740-1-1AR1R1    "  # GIS GISLINK (space-padded) — matches roll GIS_Link
    roll = {"13740-1-1AR1R1": RollRecord("51", "F1A", "commercial", False)}
    enrich_from_roll(p, roll)
    assert p.property_type == "commercial"
    assert p.land_use_code == "F1A"
    assert normalize(p)["meets_buy_box"] is True


def test_enrich_church_kept_but_marked_exempt():
    p = RawParcel(apn="A2", county="Tarrant", acres=12, property_type="church")
    p.gis_link = "77-2-3"
    roll = {"77-2-3": RollRecord("88", "X", None, True)}
    enrich_from_roll(p, roll)
    assert p.property_type == "church"  # roll type None -> keep church
    assert p.tax_exempt is True


def test_enrich_noop_when_absent():
    p = RawParcel(apn="ZZ", county="Tarrant", acres=20, property_type="church")
    p.gis_link = "1-2-3"
    enrich_from_roll(p, {})
    assert p.property_type == "church"
    assert p.tax_exempt is None
