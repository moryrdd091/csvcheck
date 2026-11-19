from dataclasses import dataclass
from pathlib import Path

from csvcheck.reader import CsvParseError, read_csv
from csvcheck.validation import ValidationResult, validate_contacts


@dataclass(frozen=True)
class AnalysisError:
    code: str
    message: str
    record_number: int | None
    line_start: int | None


@dataclass(frozen=True)
class AnalysisCompleted:
    validation: ValidationResult


@dataclass(frozen=True)
class AnalysisFailed:
    error: AnalysisError


def analyze_contacts(path: Path) -> AnalysisCompleted | AnalysisFailed:
    """Orchestrer la lecture et la validation d'un fichier de contacts."""
    try:
        csv_data = read_csv(path)
    except CsvParseError as error:
        return AnalysisFailed(
            error=AnalysisError(
                code="CSV_PARSE_ERROR",
                message=str(error),
                record_number=error.record_number,
                line_start=error.line_start,
            )
        )

    return AnalysisCompleted(validation=validate_contacts(csv_data))