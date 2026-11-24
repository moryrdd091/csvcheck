import json
from datetime import datetime
from pathlib import Path

import pytest

from csvcheck import reports as reports_module
from csvcheck.reader import read_csv
from csvcheck.reports import build_anomalies_csv, build_html_report, write_reports
from csvcheck.validation import Anomaly, ValidationResult, validate_contacts


TESTS_DIR = Path(__file__).resolve().parent


def _expected_csv_from_reference(anomalies):
    lines = ["record_number;line_start;line_end;column_index;rule"]
    for anomaly in anomalies:
        references = [
            "" if anomaly[field] is None else str(anomaly[field])
            for field in ("record_number", "line_start", "line_end", "column_index")
        ]
        lines.append(";".join([*references, anomaly["rule"]]))
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize(
    "fixture_name",
    [
        "contacts_propres",
        "contacts_anomalies",
        "colonnes_manquantes",
    ],
)
def test_anomalies_csv_content_matches_reference(fixture_name):
    source = TESTS_DIR / "fixtures" / f"{fixture_name}.csv"
    expected_path = TESTS_DIR / "expected" / f"{fixture_name}.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    validation = validate_contacts(read_csv(source))
    content = build_anomalies_csv(validation)

    assert content == _expected_csv_from_reference(expected["anomalies"])


def test_anomalies_csv_header_only_without_anomalies():
    source = TESTS_DIR / "fixtures" / "contacts_propres.csv"

    validation = validate_contacts(read_csv(source))
    content = build_anomalies_csv(validation)

    assert content == "record_number;line_start;line_end;column_index;rule\n"


def test_anomalies_csv_uses_lf_endings_only():
    source = TESTS_DIR / "fixtures" / "contacts_anomalies.csv"

    validation = validate_contacts(read_csv(source))
    content = build_anomalies_csv(validation)

    assert "\r" not in content
    assert content.endswith("\n")


@pytest.mark.parametrize(
    ("fixture_name", "expected_status"),
    [
        pytest.param("contacts_propres", "clean", id="clean"),
        pytest.param("contacts_anomalies", "data_anomalies", id="data-anomalies"),
        pytest.param("colonnes_manquantes", "schema_anomalies", id="schema-anomalies"),
    ],
)
def test_html_report_presents_context_and_status(fixture_name, expected_status):
    source = TESTS_DIR / "fixtures" / f"{fixture_name}.csv"

    validation = validate_contacts(read_csv(source))
    report = build_html_report(
        validation,
        source_name=f"{fixture_name}.csv",
        separator=";",
    )

    assert expected_status in report
    assert "contacts-v1" in report
    assert "UTF-8" in report
    assert f"{fixture_name}.csv" in report


def test_html_report_lists_anomalies_with_codes():
    source = TESTS_DIR / "fixtures" / "contacts_anomalies.csv"

    validation = validate_contacts(read_csv(source))
    report = build_html_report(
        validation,
        source_name="contacts_anomalies.csv",
        separator=";",
    )

    for rule in ("DUPLICATE_EMAIL", "REQUIRED_VALUE", "EMAIL_FORMAT"):
        assert rule in report
    assert "Aucune anomalie" not in report


def test_html_report_mentions_no_anomalies_when_clean():
    source = TESTS_DIR / "fixtures" / "contacts_propres.csv"

    validation = validate_contacts(read_csv(source))
    report = build_html_report(
        validation,
        source_name="contacts_propres.csv",
        separator=";",
    )

    assert "Aucune anomalie" in report


def test_html_report_identifies_missing_columns_and_skipped_values():
    source = TESTS_DIR / "fixtures" / "colonnes_manquantes.csv"

    validation = validate_contacts(read_csv(source))
    report = build_html_report(
        validation,
        source_name="colonnes_manquantes.csv",
        separator=";",
    )

    for column_name in validation.missing_columns:
        assert column_name in report
    assert "pas été évaluées" in report
    assert "non déterminé" in report


def test_html_report_escapes_text_from_input():
    malicious_column = '<script>alert("xss")</script>'
    validation = ValidationResult(
        profile="contacts-v1",
        status="schema_anomalies",
        records_total=0,
        records_evaluated=0,
        records_affected=None,
        missing_columns=(malicious_column,),
        data_checks="not_evaluated",
        anomalies=(
            Anomaly(
                record_number=None,
                line_start=None,
                line_end=None,
                column_index=None,
                rule="MISSING_COLUMN",
            ),
        ),
    )

    report = build_html_report(
        validation,
        source_name='<img src="x" onerror="alert(1)">',
        separator=";",
    )

    assert malicious_column not in report
    assert '<img src=' not in report
    assert "&lt;script&gt;" in report
    assert "&lt;img src=" in report


def test_html_report_contains_no_script_or_remote_resource():
    source = TESTS_DIR / "fixtures" / "contacts_anomalies.csv"

    validation = validate_contacts(read_csv(source))
    report = build_html_report(
        validation,
        source_name="contacts_anomalies.csv",
        separator=";",
    )

    assert "<script" not in report
    assert "http://" not in report
    assert "https://" not in report


def test_html_report_never_copies_cell_values(tmp_path):
    source = tmp_path / "confidentiel.csv"
    source.write_text(
        "id;nom;email\n0001;ValeurConfidentielle99;\n",
        encoding="utf-8",
    )

    validation = validate_contacts(read_csv(source))
    report = build_html_report(
        validation,
        source_name="confidentiel.csv",
        separator=";",
    )

    assert "ValeurConfidentielle99" not in report


def test_write_reports_creates_new_directory_with_both_files(tmp_path):
    source = TESTS_DIR / "fixtures" / "contacts_anomalies.csv"
    output_base = tmp_path / "rapports"
    validation = validate_contacts(read_csv(source))

    directory = write_reports(
        validation,
        output_base,
        source_name="contacts_anomalies.csv",
        separator=";",
        clock=lambda: datetime(2026, 11, 23, 14, 30, 5),
    )

    assert directory == output_base / "20261123-143005"
    anomalies_csv = (directory / "anomalies.csv").read_text(encoding="utf-8")
    html_report = (directory / "rapport.html").read_text(encoding="utf-8")
    assert anomalies_csv.startswith("record_number;")
    assert "data_anomalies" in html_report


def test_write_reports_never_overwrites_existing_directory(tmp_path):
    output_base = tmp_path / "rapports"

    def fixed_clock():
        return datetime(2026, 11, 23, 14, 30, 5)

    validation = validate_contacts(
        read_csv(TESTS_DIR / "fixtures" / "contacts_anomalies.csv")
    )
    first = write_reports(
        validation,
        output_base,
        source_name="contacts_anomalies.csv",
        separator=";",
        clock=fixed_clock,
    )
    first_csv = (first / "anomalies.csv").read_text(encoding="utf-8")

    clean_validation = validate_contacts(
        read_csv(TESTS_DIR / "fixtures" / "contacts_propres.csv")
    )
    second = write_reports(
        clean_validation,
        output_base,
        source_name="contacts_propres.csv",
        separator=";",
        clock=fixed_clock,
    )

    assert first != second
    assert second.name == "20261123-143005-1"
    assert (first / "anomalies.csv").read_text(encoding="utf-8") == first_csv


def test_write_reports_cleans_up_on_generation_failure(tmp_path, monkeypatch):
    source = TESTS_DIR / "fixtures" / "contacts_propres.csv"
    output_base = tmp_path / "rapports"

    def failing_builder(*_args, **_kwargs):
        raise OSError("échec simulée")

    monkeypatch.setattr(reports_module, "build_html_report", failing_builder)

    validation = validate_contacts(read_csv(source))

    with pytest.raises(OSError, match="échec simulée"):
        write_reports(
            validation,
            output_base,
            source_name="contacts_propres.csv",
            separator=";",
            clock=lambda: datetime(2026, 11, 23, 14, 30, 5),
        )

    assert not any(output_base.iterdir())


def test_write_reports_never_alters_source_file(tmp_path):
    source = tmp_path / "contacts.csv"
    source.write_text(
        "id;nom;email\n0001;Personne Alpha;alpha@example.com\n",
        encoding="utf-8",
    )
    original_bytes = source.read_bytes()
    output_base = tmp_path / "rapports"

    validation = validate_contacts(read_csv(source))
    write_reports(
        validation,
        output_base,
        source_name="contacts.csv",
        separator=";",
        clock=lambda: datetime(2026, 11, 23, 14, 30, 5),
    )

    assert source.read_bytes() == original_bytes