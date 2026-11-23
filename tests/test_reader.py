import csv
import hashlib
import json
from pathlib import Path

import pytest

from csvcheck.reader import CsvParseError, CsvReadError, read_csv
from csvcheck import reader as reader_module


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


def test_malformed_csv_error_has_record_and_line_references():
    source = TESTS_DIR / "fixtures" / "csv_malforme.csv"
    expected_path = TESTS_DIR / "expected" / "csv_malforme.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    with pytest.raises(CsvParseError) as error:
        read_csv(source)

    assert isinstance(error.value, csv.Error)
    assert error.value.record_number == expected["error_record_number"]
    assert error.value.line_start == expected["error_line_start"]


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


def test_read_header_only_csv(tmp_path):
    source = tmp_path / "header_only.csv"
    content = b"id;nom;email\n"
    source.write_bytes(content)

    result = read_csv(source)

    assert result.header == ("id", "nom", "email")
    assert result.records == ()
    assert result.physical_lines_total == 1
    assert source.read_bytes() == content


@pytest.mark.parametrize(
    "csv_content",
    [
        pytest.param(
            "",
            id="empty-file",
        ),
        pytest.param(
            "id;;email\n",
            id="empty-column-name",
        ),
        pytest.param(
            "id;   ;email\n",
            id="whitespace-column-name",
        ),
        pytest.param(
            "id;nom;email;nom\n",
            id="duplicate-column-name",
        ),
        pytest.param(
            "id;nom;email\n0001;Personne Alpha\n",
            id="too-few-fields",
        ),
        pytest.param(
            "id;nom;email\n0001;Personne Alpha;alpha@example.com;extra\n",
            id="too-many-fields",
        ),
        pytest.param(
            "id;nom;email\n\n",
            id="empty-data-line",
        ),
    ],
)
def test_reject_invalid_csv_structure(tmp_path, csv_content):
    source = tmp_path / "invalid_structure.csv"
    original_bytes = csv_content.encode("utf-8")
    source.write_bytes(original_bytes)

    with pytest.raises(ValueError):
        read_csv(source)

    assert source.read_bytes() == original_bytes


@pytest.mark.parametrize(
    ("prefix", "delimiter", "line_ending"),
    [
        pytest.param("\ufeff", ";", "\n", id="utf8-bom"),
        pytest.param("", ";", "\r\n", id="crlf"),
        pytest.param("", ",", "\n", id="explicit-comma"),
    ],
)
def test_read_supported_csv_variants(
    tmp_path,
    prefix,
    delimiter,
    line_ending,
):
    source = tmp_path / "variant.csv"
    header = delimiter.join(("id", "nom", "email"))
    row = delimiter.join(("0001", "Personne Alpha", "alpha@example.com"))
    content = f"{prefix}{header}{line_ending}{row}{line_ending}"
    original_bytes = content.encode("utf-8")
    source.write_bytes(original_bytes)

    result = read_csv(source, delimiter=delimiter)

    assert result.header == ("id", "nom", "email")
    assert result.physical_lines_total == 2
    assert len(result.records) == 1

    record = result.records[0]
    assert record.number == 1
    assert record.line_start == 2
    assert record.line_end == 2
    assert record.values == {
        "id": "0001",
        "nom": "Personne Alpha",
        "email": "alpha@example.com",
    }

    assert source.read_bytes() == original_bytes


@pytest.mark.parametrize(
    "invalid_bytes",
    [
        pytest.param(
            b"id;nom;email\n0001;\xff;alpha@example.com\n",
            id="invalid-utf8-byte",
        ),
        pytest.param(
            b"id;nom;email\n0001;Personne Alpha;alpha@example.com\xc3",
            id="incomplete-utf8-sequence",
        ),
    ],
)
def test_reject_invalid_utf8_without_altering_source(
    tmp_path,
    invalid_bytes,
):
    source = tmp_path / "invalid_utf8.csv"
    source.write_bytes(invalid_bytes)

    with pytest.raises(CsvReadError) as error:
        read_csv(source)

    assert error.value.code == "INVALID_UTF8"
    assert source.read_bytes() == invalid_bytes


@pytest.mark.parametrize(
    ("file_size", "should_fail"),
    [
        pytest.param(64, False, id="exact-file-size-limit"),
        pytest.param(65, True, id="above-file-size-limit"),
    ],
)
def test_file_size_limit(tmp_path, monkeypatch, file_size, should_fail):
    monkeypatch.setattr(reader_module, "MAX_FILE_SIZE_BYTES", 64)

    source = tmp_path / "size_limit.csv"
    prefix = b"id;nom;email;notes\n0001;Alpha;alpha@example.com;"
    padding = b"x" * (file_size - len(prefix) - 1)
    original_bytes = prefix + padding + b"\n"
    source.write_bytes(original_bytes)

    assert source.stat().st_size == file_size

    if should_fail:
        with pytest.raises(ValueError, match="taille"):
            read_csv(source)
    else:
        result = read_csv(source)
        assert len(result.records) == 1

    assert source.read_bytes() == original_bytes


@pytest.mark.parametrize(
    ("field_size", "should_fail"),
    [
        pytest.param(100_000, False, id="exact-field-size-limit"),
        pytest.param(100_001, True, id="above-field-size-limit"),
    ],
)
def test_field_size_limit(tmp_path, field_size, should_fail):
    source = tmp_path / "field_size.csv"
    notes = "é" * field_size
    content = (
        "id;nom;email;notes\n"
        f"0001;Alpha;alpha@example.com;{notes}\n"
    )
    original_bytes = content.encode("utf-8")
    source.write_bytes(original_bytes)

    if should_fail:
        with pytest.raises(ValueError, match="champ"):
            read_csv(source)
    else:
        result = read_csv(source)
        assert len(result.records) == 1
        assert result.records[0].values["notes"] == notes

    assert source.read_bytes() == original_bytes


def test_default_size_limits():
    assert reader_module.MAX_FILE_SIZE_BYTES == 52_428_800  # 50 Mio
    assert reader_module.MAX_FIELD_SIZE_CHARACTERS == 100_000  # 100,000 characters


@pytest.mark.parametrize(
    ("field_size", "should_fail"),
    [
        pytest.param(100_000, False, id="exact-header-field-size-limit"),
        pytest.param(100_001, True, id="above-header-field-size-limit"),
    ],
)
def test_header_field_size_limit(tmp_path, field_size, should_fail):
    source = tmp_path / "header_field_size.csv"
    column_name = "é" * field_size
    original_bytes = f"{column_name}\n".encode("utf-8")
    source.write_bytes(original_bytes)

    if should_fail:
        with pytest.raises(ValueError, match="champ"):
            read_csv(source)
    else:
        result = read_csv(source)
        assert result.header == (column_name,)
        assert result.records == ()
        assert result.physical_lines_total == 1

    assert source.read_bytes() == original_bytes