"""CLI : extraction des prises de parole des séances OCR + NER en chunks JSON."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table

from .chunker import Turn, split_turns
from .reader import Session, load_session, parse_filename

console = Console(stderr=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="impresso-chunks",
        description="Extrait les prises de parole (chunks) des séances OCR + NER du JORF.",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        default=[Path("data")],
        help="fichiers de séance ou dossiers les contenant (défaut : data/)",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("output"), help="dossier de sortie (défaut : output/)"
    )
    parser.add_argument(
        "-n", "--dry-run", action="store_true", help="découpe sans écrire de fichiers"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="logs de débogage")
    return parser


def setup_logging(verbose: bool) -> None:
    logger.remove()
    logger.add(
        RichHandler(console=console, show_time=False, show_path=False, markup=False),
        format="{message}",
        level="DEBUG" if verbose else "INFO",
    )


def collect_inputs(inputs: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in inputs:
        candidates = sorted(path.glob("*.json")) if path.is_dir() else [path]
        for candidate in candidates:
            if parse_filename(candidate) is None:
                logger.debug(f"ignoré (nom hors format date_chambre_ark) : {candidate}")
                continue
            files.append(candidate)
    return files


def chunk_record(session: Session, turn: Turn, created: str) -> dict:
    return {
        "session": session.name,
        "chamber": session.chamber_name,
        "date": session.date,
        "created": created,
        "blocks": turn.blocks,
        "spk_uuid": turn.spk.uuid,
        "content": {
            "section": turn.section,
            "subsections": turn.subsections,
            "text": turn.text,
        },
    }


def write_chunks(session: Session, turns: list[Turn], output: Path) -> Path:
    session_dir = output / session.chamber / session.ark
    session_dir.mkdir(parents=True, exist_ok=True)
    for stale in session_dir.glob("chunk_*.json"):
        stale.unlink()
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for i, turn in enumerate(turns, start=1):
        record = chunk_record(session, turn, created)
        (session_dir / f"chunk_{i:04d}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return session_dir


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.verbose)

    files = collect_inputs(args.inputs)
    if not files:
        logger.error("aucun fichier de séance trouvé")
        return 1

    summary = Table(title="Chunks extraits")
    for column in ("Séance", "Chambre", "Chunks", "SPK rejetées", "Blocs orphelins"):
        summary.add_column(column, justify="left" if column in ("Séance", "Chambre") else "right")

    total = errors = 0
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Séances", total=len(files))
        for path in files:
            progress.update(task, description=path.stem)
            try:
                session = load_session(path)
                turns, stats = split_turns(session)
            except Exception:
                logger.exception(f"échec sur {path}")
                errors += 1
                progress.advance(task)
                continue
            if not args.dry_run:
                session_dir = write_chunks(session, turns, args.output)
                logger.debug(f"{len(turns)} chunks → {session_dir}")
            total += stats.turns
            summary.add_row(
                session.name,
                session.chamber,
                str(stats.turns),
                str(stats.rejected_spk),
                str(stats.orphan_blocks),
            )
            progress.advance(task)

    console.print(summary)
    logger.info(
        f"{total} chunks pour {len(files) - errors} séances"
        + (" (dry-run, rien d'écrit)" if args.dry_run else f" → {args.output}/")
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
