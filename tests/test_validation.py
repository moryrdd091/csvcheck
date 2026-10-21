import json
from dataclasses import asdict
from pathlib import Path

import pytest

from csvcheck import validation as validation_module
from csvcheck.reader import CsvReadResult, CsvRecord, read_csv
from csvcheck.validation import (
    Anomaly,
    find_duplicate_email_anomalies,
    find_email_format_anomalies,
    find_missing_columns,
    find_required_value_anomalies,
    validate_contacts,
)


TESTS_DIR = Path(__file__).resolve().parent


@pytest.mark.parametrize(
    ("header", "expected_missing"),
    [
        pytest.param(
            ("id", "nom", "email"),
            (),
            id="required-columns-present",
        ),
        pytest.param(
            ("notes", "email", "id", "nom"),
            (),
            id="reordered-columns-with-extra",
        ),
        pytest.param(
            ("id", "nom", "telephone"),
            ("email",),
            id="missing-email",
        ),
        pytest.param(
            ("notes",),
            ("id", "nom", "email"),
            id="all-required-columns-missing",
        ),
        pytest.param(
            ("id", "nom", "Email"),
            ("email",),
            id="column-names-are-case-sensitive",
        ),
        pytest.param(
            ("id", "nom", " email"),
            ("email",),
            id="column-names-are-not-trimmed",
        ),
    ],
)
def test_find_missing_columns(header, expected_missing):
    assert find_missing_columns(header) == expected_missing


def test_find_required_value_anomalies_in_reference_csv():
    source = TESTS_DIR / "fixtures" / "contacts_anomalies.csv"
    expected_path = TESTS_DIR / "expected" / "contacts_anomalies.json"

    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    expected_anomalies = [
        anomaly
        for anomaly in expected["anomalies"]
        if anomaly["rule"] == "REQUIRED_VALUE"
    ]

    csv_data = read_csv(source)
    anomalies = find_required_value_anomalies(csv_data)

    assert len(expected_anomalies) == 1
    assert [asdict(anomaly) for anomaly in anomalies] == expected_anomalies


@pytest.mark.parametrize(
    ("column_name", "column_index"),
    [
        ("id", 4),
        ("nom", 3),
        ("email", 2),
    ],
)
@pytest.mark.parametrize(
    "empty_value",
    ["", "   ", "\t"],
    ids=["empty", "spaces", "tab"],
)
def test_required_values_with_reordered_columns(
    column_name,
    column_index,
    empty_value,
):
    values = {
        "notes": "",
        "email": "alpha@example.com",
        "nom": "Personne Alpha",
        "id": "0001",
    }
    values[column_name] = empty_value
    original_values = values.copy()

    record = CsvRecord(
        number=1,
        line_start=2,
        line_end=2,
        values=values,
    )
    csv_data = CsvReadResult(
        header=("notes", "email", "nom", "id"),
        records=(record,),
        physical_lines_total=2,
    )

    anomalies = find_required_value_anomalies(csv_data)

    assert anomalies == (
        Anomaly(
            record_number=1,
            line_start=2,
            line_end=2,
            column_index=column_index,
            rule="REQUIRED_VALUE",
        ),
    )
    assert values == original_values


def test_no_required_value_anomalies_in_clean_csv():
    source = TESTS_DIR / "fixtures" / "contacts_propres.csv"

    csv_data = read_csv(source)

    assert find_required_value_anomalies(csv_data) == ()


def test_multiple_required_value_anomalies_follow_input_order():
    records = (
        CsvRecord(
            number=1,
            line_start=2,
            line_end=2,
            values={"email": "", "notes": "", "id": "", "nom": ""},
        ),
        CsvRecord(
            number=2,
            line_start=3,
            line_end=3,
            values={
                "email": "bravo@example.com",
                "notes": "",
                "id": "",
                "nom": "Personne Bravo",
            },
        ),
    )
    original_values = [record.values.copy() for record in records]
    csv_data = CsvReadResult(
        header=("email", "notes", "id", "nom"),
        records=records,
        physical_lines_total=3,
    )

    anomalies = find_required_value_anomalies(csv_data)

    assert [
        (
            anomaly.record_number,
            anomaly.line_start,
            anomaly.line_end,
            anomaly.column_index,
            anomaly.rule,
        )
        for anomaly in anomalies
    ] == [
        (1, 2, 2, 1, "REQUIRED_VALUE"),
        (1, 2, 2, 3, "REQUIRED_VALUE"),
        (1, 2, 2, 4, "REQUIRED_VALUE"),
        (2, 3, 3, 3, "REQUIRED_VALUE"),
    ]
    assert len(anomalies) == 4
    assert len({anomaly.record_number for anomaly in anomalies}) == 2
    assert [record.values for record in records] == original_values


def test_required_value_check_rejects_incomplete_schema():
    csv_data = CsvReadResult(
        header=("id", "nom"),
        records=(
            CsvRecord(
                number=1,
                line_start=2,
                line_end=2,
                values={"id": "0001", "nom": "Personne Alpha"},
            ),
        ),
        physical_lines_total=2,
    )

    with pytest.raises(ValueError, match="colonnes obligatoires absentes"):
        find_required_value_anomalies(csv_data)


def test_find_email_format_anomalies_in_reference_csv():
    source = TESTS_DIR / "fixtures" / "contacts_anomalies.csv"
    expected_path = TESTS_DIR / "expected" / "contacts_anomalies.json"

    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    expected_anomalies = [
        anomaly
        for anomaly in expected["anomalies"]
        if anomaly["rule"] == "EMAIL_FORMAT"
    ]

    csv_data = read_csv(source)
    anomalies = find_email_format_anomalies(csv_data)

    assert len(expected_anomalies) == 1
    assert [asdict(anomaly) for anomaly in anomalies] == expected_anomalies


@pytest.mark.parametrize(
    ("email", "expected_invalid"),
    [
        pytest.param("alpha@example.com", False, id="simple-address"),
        pytest.param(
            "prenom.nom+tag@example.co.uk",
            False,
            id="address-with-tag",
        ),
        pytest.param("Alpha@example.com", False, id="uppercase-preserved"),
        pytest.param("personne@example", True, id="missing-domain-dot"),
        pytest.param("personne.example.com", True, id="missing-at-sign"),
        pytest.param("a@@example.com", True, id="multiple-at-signs"),
        pytest.param(" alpha@example.com", True, id="leading-space"),
        pytest.param("alpha@example.com ", True, id="trailing-space"),
        pytest.param("alpha@\texample.com", True, id="internal-tab"),
        pytest.param("", False, id="missing-empty"),
        pytest.param("   ", False, id="missing-spaces"),
        pytest.param("\t", False, id="missing-tab"),
    ],
)
def test_email_format_rules(email, expected_invalid):
    values = {
        "notes": "",
        "email": email,
        "id": "0001",
        "nom": "Personne Alpha",
    }
    original_values = values.copy()
    csv_data = CsvReadResult(
        header=("notes", "email", "id", "nom"),
        records=(
            CsvRecord(
                number=1,
                line_start=2,
                line_end=2,
                values=values,
            ),
        ),
        physical_lines_total=2,
    )

    anomalies = find_email_format_anomalies(csv_data)

    if expected_invalid:
        assert anomalies == (
            Anomaly(
                record_number=1,
                line_start=2,
                line_end=2,
                column_index=2,
                rule="EMAIL_FORMAT",
            ),
        )
    else:
        assert anomalies == ()

    assert values == original_values


def test_find_duplicate_email_anomalies_in_reference_csv():
    source = TESTS_DIR / "fixtures" / "contacts_anomalies.csv"
    expected_path = TESTS_DIR / "expected" / "contacts_anomalies.json"

    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    expected_anomalies = [
        anomaly
        for anomaly in expected["anomalies"]
        if anomaly["rule"] == "DUPLICATE_EMAIL"
    ]

    csv_data = read_csv(source)
    anomalies = find_duplicate_email_anomalies(csv_data)

    assert len(expected_anomalies) == 2
    assert [asdict(anomaly) for anomaly in anomalies] == expected_anomalies


@pytest.mark.parametrize(
    ("emails", "expected_records"),
    [
        pytest.param(
            (),
            (),
            id="no-records",
        ),
        pytest.param(
            ("a@example.com", "b@example.com"),
            (),
            id="unique-addresses",
        ),
        pytest.param(
            ("a@example.com", "a@example.com"),
            (1, 2),
            id="two-occurrences",
        ),
        pytest.param(
            ("a@example.com", "a@example.com", "a@example.com"),
            (1, 2, 3),
            id="three-occurrences",
        ),
        pytest.param(
            ("a@example.com", "b@example.com", "a@example.com", "b@example.com"),
            (1, 2, 3, 4),
            id="interleaved-groups",
        ),
        pytest.param(
            ("a@example.com", "A@example.com"),
            (),
            id="case-sensitive-comparison",
        ),
        pytest.param(
            ("", "", "   ", "   ", "\t", "\t"),
            (),
            id="missing-values-excluded",
        ),
        pytest.param(
            ("adresse-invalide", "adresse-invalide"),
            (),
            id="invalid-formats-excluded",
        ),
        pytest.param(
            (" a@example.com", " a@example.com", "a@example.com", "a@example.com"),
            (3, 4),
            id="invalid-and-valid-addresses",
        ),
    ],
)
def test_duplicate_email_rules(emails, expected_records):
    records = tuple(
        CsvRecord(
            number=number,
            line_start=number + 1,
            line_end=number + 1,
            values={
                "notes": "",
                "email": email,
                "id": f"{number:04d}",
                "nom": f"Personne {number}",
            },
        )
        for number, email in enumerate(emails, start=1)
    )
    original_values = [record.values.copy() for record in records]
    csv_data = CsvReadResult(
        header=("notes", "email", "id", "nom"),
        records=records,
        physical_lines_total=len(records) + 1,
    )

    anomalies = find_duplicate_email_anomalies(csv_data)

    assert anomalies == tuple(
        Anomaly(
            record_number=number,
            line_start=number + 1,
            line_end=number + 1,
            column_index=2,
            rule="DUPLICATE_EMAIL",
        )
        for number in expected_records
    )
    assert [record.values for record in records] == original_values


@pytest.mark.parametrize(
    "fixture_name",
    [
        "contacts_propres",
        "contacts_anomalies",
        "colonnes_manquantes",
    ],
)
def test_validate_contacts_against_reference(fixture_name):
    source = TESTS_DIR / "fixtures" / f"{fixture_name}.csv"
    expected_path = TESTS_DIR / "expected" / f"{fixture_name}.json"

    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    csv_data = read_csv(source)
    original_values = [
        record.values.copy()
        for record in csv_data.records
    ]

    result = validate_contacts(csv_data)

    assert result.profile == expected["profile"]
    assert result.status == expected["status"]
    assert result.records_total == expected["records_total"]
    assert result.records_evaluated == expected["records_evaluated"]
    assert result.records_affected == expected["records_affected"]
    assert result.anomaly_count == expected["anomaly_count"]
    assert result.missing_columns == tuple(
        expected.get("missing_columns", [])
    )
    assert result.data_checks == expected.get("data_checks", "evaluated")
    assert [
        asdict(anomaly)
        for anomaly in result.anomalies
    ] == expected["anomalies"]

    assert [
        record.values
        for record in csv_data.records
    ] == original_values


def test_validate_contacts_orders_anomalies_and_counts_affected_records():
    csv_data = CsvReadResult(
        header=("notes", "email", "nom", "id"),
        records=(
            CsvRecord(
                number=1,
                line_start=2,
                line_end=2,
                values={
                    "notes": "",
                    "email": "alpha@example.com",
                    "nom": "",
                    "id": "",
                },
            ),
            CsvRecord(
                number=2,
                line_start=3,
                line_end=3,
                values={
                    "notes": "",
                    "email": "alpha@example.com",
                    "nom": "Personne Bravo",
                    "id": "0002",
                },
            ),
        ),
        physical_lines_total=3,
    )
    original_values = [
        record.values.copy()
        for record in csv_data.records
    ]

    result = validate_contacts(csv_data)

    assert result.status == "data_anomalies"
    assert result.records_total == 2
    assert result.records_evaluated == 2
    assert result.records_affected == 2
    assert result.anomaly_count == 4

    assert [
        (
            anomaly.record_number,
            anomaly.column_index,
            anomaly.rule,
        )
        for anomaly in result.anomalies
    ] == [
        (1, 2, "DUPLICATE_EMAIL"),
        (1, 3, "REQUIRED_VALUE"),
        (1, 4, "REQUIRED_VALUE"),
        (2, 2, "DUPLICATE_EMAIL"),
    ]

    assert [
        record.values
        for record in csv_data.records
    ] == original_values


def test_validate_contacts_with_no_records():
    csv_data = CsvReadResult(
        header=("id", "nom", "email"),
        records=(),
        physical_lines_total=1,
    )

    result = validate_contacts(csv_data)

    assert result.status == "clean"
    assert result.records_total == 0
    assert result.records_evaluated == 0
    assert result.records_affected == 0
    assert result.anomaly_count == 0
    assert result.anomalies == ()
    assert result.missing_columns == ()
    assert result.data_checks == "evaluated"


def test_validate_contacts_skips_value_checks_for_incomplete_schema(
    monkeypatch,
):
    source = TESTS_DIR / "fixtures" / "colonnes_manquantes.csv"
    csv_data = read_csv(source)

    def forbidden_check(_csv_data):
        pytest.fail(
            "Un contrôle des valeurs a été appelé malgré le schéma incomplet."
        )

    for function_name in (
        "find_required_value_anomalies",
        "find_email_format_anomalies",
        "find_duplicate_email_anomalies",
    ):
        monkeypatch.setattr(
            validation_module,
            function_name,
            forbidden_check,
        )

    result = validate_contacts(csv_data)

    assert result.status == "schema_anomalies"
    assert result.missing_columns == ("email",)
    assert result.records_total == 2
    assert result.records_evaluated == 0
    assert result.records_affected is None
    assert result.data_checks == "not_evaluated"
    assert result.anomalies == (
        Anomaly(
            record_number=None,
            line_start=None,
            line_end=None,
            column_index=None,
            rule="MISSING_COLUMN",
        ),
    )
    assert result.anomaly_count == 1