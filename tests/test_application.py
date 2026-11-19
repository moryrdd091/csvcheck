import json
from dataclasses import asdict
from pathlib import Path

import pytest

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