import json
import subprocess
import sys
from pathlib import Path

import pytest

from csvcheck.cli import main


TESTS_DIR = Path(__file__).resolve().parent


@pytest.mark.parametrize(
    ("fixture_name", "expected_exit_code", "expected_status"),
    [
        pytest.param("contacts_propres", 0, "clean", id="clean-exit-0"),
        pytest.param(
            "contacts_anomalies", 1, "data_anomalies", id="data-anomalies-exit-1"
        ),
        pytest.param(
            "colonnes_manquantes", 1, "schema_anomalies", id="schema-anomalies-exit-1"
        ),
    ],
)
def test_cli_exit_codes_and_summary_for_completed_analyses(
    capsys, fixture_name, expected_exit_code, expected_status
):
    source = str(TESTS_DIR / "fixtures" / f"{fixture_name}.csv")

    exit_code = main([source])
    captured = capsys.readouterr()

    assert exit_code == expected_exit_code
    assert expected_status in captured.out
    assert captured.err == ""


def test_cli_reports_error_on_stderr_for_malformed_csv(capsys):
    source = str(TESTS_DIR / "fixtures" / "csv_malforme.csv")
    expected_path = TESTS_DIR / "expected" / "csv_malforme.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    exit_code = main([source])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert expected["error_code"] in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_cli_missing_file_reports_error(capsys):
    missing = TESTS_DIR / "fixtures" / "absent.csv"

    exit_code = main([str(missing)])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "introuvable" in captured.err
    assert "Traceback" not in captured.err


def test_cli_module_end_to_end_for_malformed_csv():
    source = TESTS_DIR / "fixtures" / "csv_malforme.csv"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "csvcheck.cli",
            str(source),
        ],
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "CSV_PARSE_ERROR" in completed.stderr
    assert "Traceback" not in completed.stderr
