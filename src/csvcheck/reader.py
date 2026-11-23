import csv
import os
from dataclasses import dataclass
from pathlib import Path

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MiB
MAX_FIELD_SIZE_CHARACTERS = 100_000  # 100 000 caractères


@dataclass(frozen=True)
class CsvRecord:
    number: int
    line_start: int
    line_end: int
    values: dict[str, str]


@dataclass(frozen=True)
class CsvReadResult:
    header: tuple[str, ...]
    records: tuple[CsvRecord, ...]
    physical_lines_total: int


class CsvReadError(ValueError):
    """Erreur bloquante de lecture, identifiée par un code stable."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        record_number: int | None = None,
        line_start: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.record_number = record_number
        self.line_start = line_start


class CsvParseError(CsvReadError, csv.Error):
    """Erreur de syntaxe CSV détectée par le module csv."""

    def __init__(
        self,
        message: str,
        *,
        record_number: int | None = None,
        line_start: int | None = None,
    ) -> None:
        super().__init__(
            "CSV_PARSE_ERROR",
            message,
            record_number=record_number,
            line_start=line_start,
        )


def _check_field_sizes(
    fields: list[str],
    *,
    record_number: int | None = None,
    line_start: int | None = None,
) -> None:
    if any(len(value) > MAX_FIELD_SIZE_CHARACTERS for value in fields):
        raise CsvReadError(
            "FIELD_SIZE_LIMIT_EXCEEDED",
            "Un champ dépasse la taille maximale autorisée.",
            record_number=record_number,
            line_start=line_start,
        )


def read_csv(
    path: Path,
    *,
    delimiter: str = ";",
) -> CsvReadResult:
    if delimiter not in (";", ","):
        raise ValueError("Le séparateur doit être un point-virgule ou une virgule.")

    records: list[CsvRecord] = []

    with path.open(encoding="utf-8-sig", newline="") as source:
        file_size = os.fstat(source.fileno()).st_size

        if file_size > MAX_FILE_SIZE_BYTES:
            raise CsvReadError(
                "FILE_SIZE_LIMIT_EXCEEDED",
                "Le fichier dépasse la taille maximale autorisée.",
            )

        reader = csv.reader(source, delimiter=delimiter, strict=True)

        try:
            header = next(reader, None)
        except UnicodeDecodeError as error:
            raise CsvReadError(
                "INVALID_UTF8",
                "Le fichier n’est pas encodé en UTF-8 valide.",
            ) from error
        except csv.Error as error:
            raise CsvParseError(
                str(error),
                line_start=1,
            ) from error

        if not header:
            raise CsvReadError(
                "NO_HEADER",
                "Le fichier ne contient pas d’en-tête exploitable.",
            )
        _check_field_sizes(header, line_start=1)

        if any(not name.strip() for name in header):
            raise CsvReadError(
                "INVALID_HEADER",
                "Un nom de colonne est vide.",
                line_start=1,
            )

        if len(header) != len(set(header)):
            raise CsvReadError(
                "INVALID_HEADER",
                "L’en-tête contient des noms de colonnes dupliqués.",
                line_start=1,
            )

        while True:
            line_start = reader.line_num + 1

            try:
                row = next(reader)
            except StopIteration:
                break
            except csv.Error as error:
                raise CsvParseError(
                    str(error),
                    record_number=len(records) + 1,
                    line_start=line_start,
                ) from error
            except UnicodeDecodeError as error:
                raise CsvReadError(
                    "INVALID_UTF8",
                    "Le fichier n’est pas encodé en UTF-8 valide.",
                ) from error

            if len(row) != len(header):
                raise CsvReadError(
                    "FIELD_COUNT_MISMATCH",
                    f"Nombre de champs incorrect à la ligne {line_start}.",
                    record_number=len(records) + 1,
                    line_start=line_start,
                )
            _check_field_sizes(
                row,
                record_number=len(records) + 1,
                line_start=line_start,
            )

            records.append(
                CsvRecord(
                    number=len(records) + 1,
                    line_start=line_start,
                    line_end=reader.line_num,
                    values=dict(zip(header, row)),
                )
            )

        physical_lines_total = reader.line_num

    return CsvReadResult(
        header=tuple(header),
        records=tuple(records),
        physical_lines_total=physical_lines_total,
    )