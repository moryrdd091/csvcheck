import csv
from dataclasses import dataclass
from pathlib import Path


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


def read_csv(
    path: Path,
    *,
    delimiter: str = ";",
) -> CsvReadResult:
    if delimiter not in (";", ","):
        raise ValueError("Le séparateur doit être un point-virgule ou une virgule.")

    records: list[CsvRecord] = []

    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source, delimiter=delimiter, strict=True)
        header = next(reader, None)

        if not header:
            raise ValueError("Le fichier ne contient pas d’en-tête exploitable.")

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

            if len(row) != len(header):
                raise ValueError(
                    f"Nombre de champs incorrect à la ligne {line_start}."
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