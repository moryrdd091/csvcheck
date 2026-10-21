import re
from collections import Counter
from dataclasses import dataclass

from csvcheck.reader import CsvReadResult


REQUIRED_COLUMNS: tuple[str, ...] = ("id", "nom", "email")
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


@dataclass(frozen=True)
class Anomaly:
    record_number: int | None
    line_start: int | None
    line_end: int | None
    column_index: int | None
    rule: str


@dataclass(frozen=True)
class ValidationResult:
    profile: str
    status: str
    records_total: int
    records_evaluated: int
    records_affected: int | None
    missing_columns: tuple[str, ...]
    data_checks: str
    anomalies: tuple[Anomaly, ...]

    @property
    def anomaly_count(self) -> int:
        return len(self.anomalies)


def find_missing_columns(header: tuple[str, ...]) -> tuple[str, ...]:
    """Retourner les colonnes obligatoires absentes, dans l’ordre du profil."""
    return tuple(
        column
        for column in REQUIRED_COLUMNS
        if column not in header
    )


def find_required_value_anomalies(
    csv_data: CsvReadResult,
) -> tuple[Anomaly, ...]:
    """Repérer les valeurs obligatoires manquantes sans modifier les données."""
    if find_missing_columns(csv_data.header):
        raise ValueError(
            "Contrôle des valeurs impossible : colonnes obligatoires absentes."
        )

    anomalies: list[Anomaly] = []

    for record in csv_data.records:
        for column_index, column_name in enumerate(csv_data.header, start=1):
            if column_name not in REQUIRED_COLUMNS:
                continue

            if not record.values[column_name].strip():
                anomalies.append(
                    Anomaly(
                        record_number=record.number,
                        line_start=record.line_start,
                        line_end=record.line_end,
                        column_index=column_index,
                        rule="REQUIRED_VALUE",
                    )
                )

    return tuple(anomalies)


def find_email_format_anomalies(
    csv_data: CsvReadResult,
) -> tuple[Anomaly, ...]:
    """Repérer les e-mails non manquants dont le format est refusé."""
    if find_missing_columns(csv_data.header):
        raise ValueError(
            "Contrôle des valeurs impossible : colonnes obligatoires absentes."
        )

    column_index = csv_data.header.index("email") + 1
    anomalies: list[Anomaly] = []

    for record in csv_data.records:
        email = record.values["email"]

        if not email.strip():
            continue

        if EMAIL_PATTERN.fullmatch(email) is None:
            anomalies.append(
                Anomaly(
                    record_number=record.number,
                    line_start=record.line_start,
                    line_end=record.line_end,
                    column_index=column_index,
                    rule="EMAIL_FORMAT",
                )
            )

    return tuple(anomalies)


def find_duplicate_email_anomalies(
    csv_data: CsvReadResult,
) -> tuple[Anomaly, ...]:
    """Signaler toutes les occurrences des e-mails admissibles dupliqués."""
    if find_missing_columns(csv_data.header):
        raise ValueError(
            "Contrôle des valeurs impossible : colonnes obligatoires absentes."
        )

    column_index = csv_data.header.index("email") + 1

    valid_email_counts = Counter(
        record.values["email"]
        for record in csv_data.records
        if EMAIL_PATTERN.fullmatch(record.values["email"]) is not None
    )

    anomalies: list[Anomaly] = []

    for record in csv_data.records:
        email = record.values["email"]

        if valid_email_counts[email] > 1:
            anomalies.append(
                Anomaly(
                    record_number=record.number,
                    line_start=record.line_start,
                    line_end=record.line_end,
                    column_index=column_index,
                    rule="DUPLICATE_EMAIL",
                )
            )

    return tuple(anomalies)


def validate_contacts(csv_data: CsvReadResult) -> ValidationResult:
    """Appliquer le profil contacts-v1 aux données déjà lues."""
    missing_columns = find_missing_columns(csv_data.header)
    records_total = len(csv_data.records)

    if missing_columns:
        anomalies = tuple(
            Anomaly(
                record_number=None,
                line_start=None,
                line_end=None,
                column_index=None,
                rule="MISSING_COLUMN",
            )
            for _ in missing_columns
        )

        return ValidationResult(
            profile="contacts-v1",
            status="schema_anomalies",
            records_total=records_total,
            records_evaluated=0,
            records_affected=None,
            missing_columns=missing_columns,
            data_checks="not_evaluated",
            anomalies=anomalies,
        )

    combined_anomalies = (
        *find_required_value_anomalies(csv_data),
        *find_email_format_anomalies(csv_data),
        *find_duplicate_email_anomalies(csv_data),
    )

    ordered_anomalies = tuple(
        sorted(
            combined_anomalies,
            key=lambda anomaly: (
                anomaly.record_number or 0,
                anomaly.column_index or 0,
                anomaly.rule,
            ),
        )
    )

    records_affected = len(
        {
            anomaly.record_number
            for anomaly in ordered_anomalies
        }
    )

    return ValidationResult(
        profile="contacts-v1",
        status="data_anomalies" if ordered_anomalies else "clean",
        records_total=records_total,
        records_evaluated=records_total,
        records_affected=records_affected,
        missing_columns=(),
        data_checks="evaluated",
        anomalies=ordered_anomalies,
    )