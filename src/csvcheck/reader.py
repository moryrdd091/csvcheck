import os
import csv
from dataclasses import dataclass
from pathlib import Path

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 Mio
MAX_FIELD_SIZE_CHARACTERS = 100_000  # 100,000 characters

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


class CsvParseError(csv.Error):
    """Erreur de syntaxe CSV avec les références de l'enregistrement concerné."""

    def __init__(
        self,
        message: str,
        *,
        record_number: int | None = None,
        line_start: int | None = None,
    ) -> None:
        super().__init__(message)
        self.record_number = record_number
        self.line_start = line_start


def _check_field_sizes(fields: list[str]) -> None:
    if any(len(value) > MAX_FIELD_SIZE_CHARACTERS for value in fields):
        raise ValueError("Un champ dépasse la taille maximale autorisée.")


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
            raise ValueError("Le fichier dépasse la taille maximale autorisée.")

        reader = csv.reader(source, delimiter=delimiter, strict=True)

        header = next(reader, None)

        if not header:
            raise ValueError("Le fichier ne contient pas d’en-tête exploitable.")
        _check_field_sizes(header)

        if any(not name.strip() for name in header):
            raise ValueError("Un nom de colonne est vide.")

        if len(header) != len(set(header)):
            raise ValueError("L’en-tête contient des noms de colonnes dupliqués.")

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

            if len(row) != len(header):
                raise ValueError(
                    f"Nombre de champs incorrect à la ligne {line_start}."
                )
            _check_field_sizes(row)

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