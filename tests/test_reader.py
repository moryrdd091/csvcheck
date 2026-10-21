import csv
import hashlib
import json
from pathlib import Path

import pytest

from csvcheck.reader import read_csv


TESTS_DIR = Path(__file__).resolve().parent


def test_read_clean_csv():
    source = TESTS_DIR / "fixtures" / "contacts_propres.csv"
    expected_path = TESTS_DIR / "expected" / "contacts_propres.json"

    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    source_hash_before = hashlib.sha256(source.read_bytes()).hexdigest()

    result = read_csv(source)

    assert result.header == (
        "id",
        "nom",
        "email",
        "telephone",
        "code_postal",
        "notes",
    )
    assert len(result.records) == expected["records_total"]
    assert result.physical_lines_total == expected["physical_lines_total"]

    checks = expected["assertions"]

    first = result.records[0]
    assert first.number == 1
    assert first.values["id"] == checks["record_1_id"]
    assert first.values["telephone"] == checks["record_1_telephone"]
    assert first.values["code_postal"] == checks["record_1_code_postal"]

    third = result.records[2]
    assert third.number == 3
    assert third.line_start == checks["record_3_line_start"]
    assert third.line_end == checks["record_3_line_end"]
    assert third.values["notes"] == checks["record_3_notes"]

    source_hash_after = hashlib.sha256(source.read_bytes()).hexdigest()
    assert source_hash_after == source_hash_before


def test_reject_malformed_csv_without_altering_source():
    source = TESTS_DIR / "fixtures" / "csv_malforme.csv"
    source_hash_before = hashlib.sha256(source.read_bytes()).hexdigest()

    with pytest.raises(csv.Error):
        read_csv(source)

    source_hash_after = hashlib.sha256(source.read_bytes()).hexdigest()
    assert source_hash_after == source_hash_before


@pytest.mark.parametrize(
    "fixture_name",
    [
        "contacts_anomalies",
        "colonnes_manquantes",
    ],
)
def test_read_structurally_valid_csv(fixture_name):
    source = TESTS_DIR / "fixtures" / f"{fixture_name}.csv"
    expected_path = TESTS_DIR / "expected" / f"{fixture_name}.json"

    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    source_hash_before = hashlib.sha256(source.read_bytes()).hexdigest()

    result = read_csv(source)

    assert len(result.records) == expected["records_total"]
    assert result.physical_lines_total == expected["physical_lines_total"]

    for record in result.records:
        assert tuple(record.values) == result.header

    source_hash_after = hashlib.sha256(source.read_bytes()).hexdigest()
    assert source_hash_after == source_hash_before