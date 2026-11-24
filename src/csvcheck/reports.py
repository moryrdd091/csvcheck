import html
import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from csvcheck.validation import ValidationResult

ANOMALIES_CSV_HEADER = "record_number;line_start;line_end;column_index;rule"


def build_anomalies_csv(validation: ValidationResult) -> str:
    """Construire le contenu du CSV d'anomalies."""
    lines = [ANOMALIES_CSV_HEADER]

    for anomaly in validation.anomalies:
        references = [
            "" if value is None else str(value)
            for value in (
                anomaly.record_number,
                anomaly.line_start,
                anomaly.line_end,
                anomaly.column_index,
            )
        ]
        lines.append(";".join([*references, anomaly.rule]))

    return "\n".join(lines) + "\n"


def _format_optional_integer(value: int | None) -> str:
    if value is None:
        return "non déterminé"
    return str(value)


def build_html_report(
    validation: ValidationResult,
    *,
    source_name: str,
    separator: str,
) -> str:
    """Construire le rapport HTML d’une analyse terminée."""
    parts = [
        "<!DOCTYPE html>",
        '<html lang="fr">',
        "<head>",
        '<meta charset="utf-8">',
        "<title>Rapport d’analyse csvcheck</title>",
        "<style>",
        "body { font-family: system-ui, sans-serif; margin: 2rem; }",
        "table { border-collapse: collapse; margin-top: 1rem; }",
        "th, td { border: 1px solid #999; padding: 0.4rem 0.8rem; text-align: left; }",
        "th { background: #eee; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Rapport d’analyse csvcheck</h1>",
        "<dl>",
        f"<dt>Statut</dt><dd>{html.escape(validation.status)}</dd>",
        f"<dt>Profil</dt><dd>{html.escape(validation.profile)}</dd>",
        "<dt>Encodage</dt><dd>UTF-8</dd>",
        f"<dt>Séparateur</dt><dd>{html.escape(separator)}</dd>",
        f"<dt>Fichier source</dt><dd>{html.escape(source_name)}</dd>",
        f"<dt>Enregistrements lus</dt><dd>{validation.records_total}</dd>",
        f"<dt>Enregistrements évalués</dt><dd>{validation.records_evaluated}</dd>",
        "<dt>Enregistrements concernés</dt><dd>"
        f"{html.escape(_format_optional_integer(validation.records_affected))}</dd>",
        f"<dt>Anomalies</dt><dd>{validation.anomaly_count}</dd>",
        "</dl>",
    ]

    if validation.missing_columns:
        parts.append("<h2>Colonnes obligatoires absentes</h2>")
        parts.append("<ul>")
        parts.extend(
            f"<li>{html.escape(column_name)}</li>"
            for column_name in validation.missing_columns
        )
        parts.append("</ul>")

    if validation.data_checks == "not_evaluated":
        parts.append("<p>Les valeurs n’ont pas été évaluées.</p>")

    if validation.anomalies:
        parts.append("<table>")
        parts.append("<caption>Anomalies</caption>")
        parts.append(
            "<thead><tr>"
            "<th>Enregistrement</th><th>Ligne de début</th><th>Ligne de fin</th>"
            "<th>Colonne</th><th>Code</th>"
            "</tr></thead>"
        )
        parts.append("<tbody>")
        for anomaly in validation.anomalies:
            cells = [
                "" if value is None else str(value)
                for value in (
                    anomaly.record_number,
                    anomaly.line_start,
                    anomaly.line_end,
                    anomaly.column_index,
                )
            ]
            cells.append(html.escape(anomaly.rule))
            parts.append("<tr>")
            parts.extend(f"<td>{cell}</td>" for cell in cells)
            parts.append("</tr>")
        parts.append("</tbody>")
        parts.append("</table>")
    else:
        parts.append("<p>Aucune anomalie détectée.</p>")

    parts.append("</body>")
    parts.append("</html>")

    return "\n".join(parts)


def _new_report_directory(output_base: Path, clock: Callable[[], datetime]) -> Path:
    timestamp = clock().strftime("%Y%m%d-%H%M%S")
    candidate = output_base / timestamp
    suffix = 1
    while candidate.exists():
        candidate = output_base / f"{timestamp}-{suffix}"
        suffix += 1
    return candidate


def write_reports(
    validation: ValidationResult,
    output_base: Path,
    *,
    source_name: str,
    separator: str,
    clock: Callable[[], datetime] = datetime.now,
) -> Path:
    """Publier les rapports dans un dossier neuf et renvoyer son chemin."""
    output_base.mkdir(parents=True, exist_ok=True)
    directory = _new_report_directory(output_base, clock)
    directory.mkdir()

    try:
        (directory / "anomalies.csv").write_text(
            build_anomalies_csv(validation),
            encoding="utf-8",
            newline="\n",
        )
        (directory / "rapport.html").write_text(
            build_html_report(
                validation,
                source_name=source_name,
                separator=separator,
            ),
            encoding="utf-8",
            newline="\n",
        )
    except BaseException:
        shutil.rmtree(directory, ignore_errors=True)
        raise

    return directory