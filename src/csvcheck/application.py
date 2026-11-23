from dataclasses import dataclass
from pathlib import Path

from csvcheck.reader import CsvReadError, read_csv
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


def _failed(
    code: str,
    message: str,
    *,
    record_number: int | None = None,
    line_start: int | None = None,
) -> AnalysisFailed:
    return AnalysisFailed(
        error=AnalysisError(
            code=code,
            message=message,
            record_number=record_number,
            line_start=line_start,
        )
    )


def analyze_contacts(
    path: Path,
    *,
    delimiter: str = ";",
) -> AnalysisCompleted | AnalysisFailed:
    """Orchestrer la lecture et la validation d'un fichier de contacts."""
    try:
        csv_data = read_csv(path, delimiter=delimiter)
    except FileNotFoundError:
        return _failed("FILE_NOT_FOUND", f"Fichier introuvable : {path}")
    except OSError:
        return _failed("UNREADABLE_FILE", f"Impossible de lire le fichier : {path}")
    except CsvReadError as error:
        return _failed(
            error.code,
            str(error),
            record_number=error.record_number,
            line_start=error.line_start,
        )

    return AnalysisCompleted(validation=validate_contacts(csv_data))