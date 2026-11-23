import json
from dataclasses import asdict
from pathlib import Path

import pytest
from csvcheck import application as application_module
from csvcheck import reader as reader_module

from csvcheck.application import (
    AnalysisCompleted,
    AnalysisFailed,
    analyze_contacts,
)


TESTS_DIR = Path(__file__).resolve().parent


@pytest.mark.parametrize(
    ("fixture_name", "expected_status"),
    [
        pytest.param("contacts_propres", "clean", id="clean"),
        pytest.param("contacts_anomalies", "data_anomalies", id="data-anomalies"),
        pytest.param(
            "colonnes_manquantes", "schema_anomalies", id="schema-anomalies"
        ),
    ],
)
def test_analyze_contacts_completes_expected_validation(
    fixture_name,
    expected_status,
):
    source = TESTS_DIR / "fixtures" / f"{fixture_name}.csv"
    expected_path = TESTS_DIR / "expected" / f"{fixture_name}.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    outcome = analyze_contacts(source)

    assert isinstance(outcome, AnalysisCompleted)
    assert outcome.validation.status == expected_status
    assert outcome.validation.profile == expected["profile"]
    assert outcome.validation.records_total == expected["records_total"]
    assert outcome.validation.records_evaluated == expected["records_evaluated"]
    assert outcome.validation.records_affected == expected["records_affected"]
    assert outcome.validation.anomaly_count == expected["anomaly_count"]
    assert [asdict(anomaly) for anomaly in outcome.validation.anomalies] == (
        expected["anomalies"]
    )


def test_analyze_contacts_fails_on_malformed_csv():
    source = TESTS_DIR / "fixtures" / "csv_malforme.csv"
    expected_path = TESTS_DIR / "expected" / "csv_malforme.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    outcome = analyze_contacts(source)

    assert isinstance(outcome, AnalysisFailed)
    assert outcome.error.code == expected["error_code"]
    assert outcome.error.record_number == expected["error_record_number"]
    assert outcome.error.line_start == expected["error_line_start"]


def test_analyze_contacts_fails_on_missing_file(tmp_path):
    outcome = analyze_contacts(tmp_path / "absent.csv")

    assert isinstance(outcome, AnalysisFailed)
    assert outcome.error.code == "FILE_NOT_FOUND"
    assert outcome.error.record_number is None
    assert outcome.error.line_start is None


def test_analyze_contacts_fails_on_unreadable_file(tmp_path, monkeypatch):
    source = tmp_path / "illisible.csv"
    source.write_text("id;nom;email\n", encoding="utf-8")

    def raise_permission_error(_path):
        raise PermissionError("accès refusé")

    monkeypatch.setattr(application_module, "read_csv", raise_permission_error)

    outcome = analyze_contacts(source)

    assert isinstance(outcome, AnalysisFailed)
    assert outcome.error.code == "UNREADABLE_FILE"


def test_analyze_contacts_fails_on_empty_file(tmp_path):
    source = tmp_path / "vide.csv"
    source.write_text("", encoding="utf-8")

    outcome = analyze_contacts(source)

    assert isinstance(outcome, AnalysisFailed)
    assert outcome.error.code == "NO_HEADER"


@pytest.mark.parametrize(
    "header_line",
    [
        pytest.param("id;;email\n", id="empty-column-name"),
        pytest.param("id; ;email\n", id="whitespace-column-name"),
        pytest.param("id;nom;id\n", id="duplicate-column-names"),
    ],
)
def test_analyze_contacts_fails_on_invalid_header(tmp_path, header_line):
    source = tmp_path / "en_tete_invalide.csv"
    source.write_text(header_line, encoding="utf-8")

    outcome = analyze_contacts(source)

    assert isinstance(outcome, AnalysisFailed)
    assert outcome.error.code == "INVALID_HEADER"
    assert outcome.error.record_number is None
    assert outcome.error.line_start == 1


def test_analyze_contacts_fails_on_field_count_mismatch(tmp_path):
    source = tmp_path / "champs_incoherents.csv"
    source.write_text(
        "id;nom;email\n0001;Personne Alpha\n",
        encoding="utf-8",
    )

    outcome = analyze_contacts(source)

    assert isinstance(outcome, AnalysisFailed)
    assert outcome.error.code == "FIELD_COUNT_MISMATCH"
    assert outcome.error.record_number == 1
    assert outcome.error.line_start == 2


def test_analyze_contacts_fails_on_file_size_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(reader_module, "MAX_FILE_SIZE_BYTES", 8)
    source = tmp_path / "trop_gros.csv"
    source.write_text(
        "id;nom;email\n0001;Alpha;alpha@example.com\n",
        encoding="utf-8",
    )

    outcome = analyze_contacts(source)

    assert isinstance(outcome, AnalysisFailed)
    assert outcome.error.code == "FILE_SIZE_LIMIT_EXCEEDED"


def test_analyze_contacts_fails_on_field_size_limit(tmp_path):
    source = tmp_path / "champ_trop_long.csv"
    source.write_text(
        "id;nom;email;notes\n"
        "0001;Alpha;alpha@example.com;" + "x" * 100_001 + "\n",
        encoding="utf-8",
    )

    outcome = analyze_contacts(source)

    assert isinstance(outcome, AnalysisFailed)
    assert outcome.error.code == "FIELD_SIZE_LIMIT_EXCEEDED"
    assert outcome.error.record_number == 1
    assert outcome.error.line_start == 2


def test_analyze_contacts_fails_on_invalid_utf8(tmp_path):
    source = tmp_path / "encodage_invalide.csv"
    source.write_bytes(b"id;nom;email\n0001;\xff;alpha@example.com\n")

    outcome = analyze_contacts(source)

    assert isinstance(outcome, AnalysisFailed)
    assert outcome.error.code == "INVALID_UTF8"


def test_analyze_contacts_fails_on_malformed_header(tmp_path):
    source = tmp_path / "en_tete_malforme.csv"
    source.write_text('id;nom;"email\n', encoding="utf-8")

    outcome = analyze_contacts(source)

    assert isinstance(outcome, AnalysisFailed)
    assert outcome.error.code == "CSV_PARSE_ERROR"
    assert outcome.error.record_number is None
    assert outcome.error.line_start == 1