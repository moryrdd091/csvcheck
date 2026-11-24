import json
import subprocess
import sys
from pathlib import Path

import pytest

from csvcheck import cli as cli_module
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
    tmp_path, capsys, fixture_name, expected_exit_code, expected_status
):
    source = str(TESTS_DIR / "fixtures" / f"{fixture_name}.csv")
    output_base = tmp_path / "rapports"

    exit_code = main(["--output", str(output_base), source])
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


def test_cli_accepts_comma_separator(tmp_path, capsys):
    source = tmp_path / "contacts_virgule.csv"
    source.write_text(
        "id,nom,email\n0001,Personne Alpha,alpha@example.com\n",
        encoding="utf-8",
    )

    exit_code = main(["--separator", ",", "--output", str(tmp_path / "rapports"), str(source)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "clean" in captured.out


def test_cli_rejects_unknown_separator(tmp_path):
    source = tmp_path / "contacts.csv"
    source.write_text("id;nom;email\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exit_info:
        main(["--separator", "|", str(source)])

    assert exit_info.value.code == 2


def test_cli_writes_reports_on_completed_analysis(tmp_path, capsys):
    source = TESTS_DIR / "fixtures" / "contacts_anomalies.csv"
    output_base = tmp_path / "rapports"

    exit_code = main(["--output", str(output_base), str(source)])
    captured = capsys.readouterr()

    assert exit_code == 1
    directories = list(output_base.iterdir())
    assert len(directories) == 1
    assert (directories[0] / "rapport.html").is_file()
    assert (directories[0] / "anomalies.csv").is_file()
    assert str(directories[0]) in captured.out


def test_cli_creates_no_report_directory_on_blocking_error(tmp_path):
    source = TESTS_DIR / "fixtures" / "csv_malforme.csv"
    output_base = tmp_path / "rapports"

    exit_code = main(["--output", str(output_base), str(source)])

    assert exit_code == 2
    assert not output_base.exists()


def test_cli_reports_generation_failure(tmp_path, capsys, monkeypatch):
    source = TESTS_DIR / "fixtures" / "contacts_propres.csv"
    output_base = tmp_path / "rapports"

    def failing_writer(*_args, **_kwargs):
        raise OSError("disque plein")

    monkeypatch.setattr(cli_module, "write_reports", failing_writer)

    exit_code = main(["--output", str(output_base), str(source)])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "Impossible de générer les rapports" in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_cli_module_end_to_end_writes_reports(tmp_path):
    source = TESTS_DIR / "fixtures" / "contacts_anomalies.csv"
    output_base = tmp_path / "rapports"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "csvcheck.cli",
            "--output",
            str(output_base),
            str(source),
        ],
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    directories = list(output_base.iterdir())
    assert len(directories) == 1
    assert (directories[0] / "rapport.html").is_file()
    assert (directories[0] / "anomalies.csv").is_file()