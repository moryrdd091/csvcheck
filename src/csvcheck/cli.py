import argparse
import sys
from pathlib import Path

from csvcheck.application import (
    AnalysisCompleted,
    AnalysisFailed,
    analyze_contacts,
)


def _print_summary(validation) -> None:
    if validation.records_affected is None:
        affected = "non déterminé"
    else:
        affected = str(validation.records_affected)

    print(f"Profil : {validation.profile}")
    print(f"Statut : {validation.status}")
    print(f"Enregistrements lus : {validation.records_total}")
    print(f"Enregistrements évalués : {validation.records_evaluated}")
    print(f"Enregistrements concernés : {affected}")
    print(f"Anomalies : {validation.anomaly_count}")


def main(argv: list[str] | None = None) -> int:
    """Analyser un fichier CSV de contacts et retourner le code de sortie."""
    parser = argparse.ArgumentParser(
        prog="csvcheck",
        description="Contrôler un fichier CSV de contacts avant import.",
    )
    parser.add_argument("fichier", help="Chemin du fichier CSV à analyser")
    parser.add_argument(
        "--separator",
        choices=[";", ","],
        default=";",
        help="Séparateur de champs du fichier CSV",
    )
    args = parser.parse_args(argv)

    path = Path(args.fichier)
    outcome = analyze_contacts(
        Path(args.fichier), delimiter=args.separator
    )

    if isinstance(outcome, AnalysisFailed):
        error = outcome.error
        location = ""
        if error.record_number is not None:
            location = (
                f" (enregistrement {error.record_number}, ligne {error.line_start})"
            )
        print(
            f"Analyse impossible : {error.code}{location} — {error.message}",
            file=sys.stderr,
        )
        return 2

    assert isinstance(outcome, AnalysisCompleted)
    _print_summary(outcome.validation)

    if outcome.validation.status == "clean":
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())