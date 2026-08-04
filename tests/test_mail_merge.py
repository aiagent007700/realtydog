"""OUTREACH-001 tests: the CSV writer (pure; the query is DB-backed and run live)."""
import csv

from app.outreach.mail_merge import _COLUMNS, write_csv


def test_write_csv_headers_and_strip(tmp_path):
    rows = [
        {"owner_name": "RUE, BART", "owner_mailing_address": "123 RANCH RD   ",  # padded
         "situs_address": "500 FARM RD", "acres": 47.95, "property_type": "ranch_with_structure",
         "motivation_score": 25},
    ]
    path = str(tmp_path / "out.csv")
    n = write_csv(rows, path)
    assert n == 1

    with open(path, newline="", encoding="utf-8") as fh:
        reader = list(csv.reader(fh))
    assert reader[0] == [label for _, label in _COLUMNS]  # human-readable header
    row = reader[1]
    assert row[0] == "RUE, BART"
    assert row[1] == "123 RANCH RD"  # trailing padding stripped
    assert "47.95" in row


def test_write_csv_missing_fields_are_blank(tmp_path):
    path = str(tmp_path / "out.csv")
    write_csv([{"owner_name": "SMITH"}], path)  # most fields absent
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert rows[1][0] == "SMITH"
    assert rows[1][1] == ""  # missing mailing address -> empty cell, no crash
