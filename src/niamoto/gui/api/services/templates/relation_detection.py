"""Helpers to infer relations between CSV stats sources and reference entities."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)


def _column_tokens(column_name: str) -> set[str]:
    tokens = {part for part in column_name.lower().split("_") if part}
    return {token for token in tokens if token not in {"id", "code", "name", "label"}}


def read_csv_columns(csv_path: Path) -> list[str]:
    """Read normalized column names from a CSV header."""
    with open(csv_path, "r", encoding="utf-8") as f:
        first_line = f.readline()
        delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    return [c.strip().lower() for c in first_line.strip().split(delimiter)]


def detect_relation_fields(
    work_dir: Path, reference_name: str, csv_path: Path, csv_columns: list[str]
) -> tuple[str, str, float]:
    """
    Infer the best reference field / CSV field pair for a stats CSV.

    Returns:
        (ref_field, match_field, score)
    """
    ref_field = f"id_{reference_name}"
    if reference_name.endswith("s"):
        ref_field = f"id_{reference_name[:-1]}"

    entity_candidates = ["plot_id", "shape_id", "taxon_id", "entity_id", "id"]
    match_field = "id"
    for candidate in csv_columns:
        normalized = candidate.lower()
        if (
            normalized in entity_candidates
            or normalized.endswith("_id")
            or normalized.endswith("_code")
            or normalized.startswith("id_")
        ):
            match_field = candidate
            break

    db_path = work_dir / "db" / "niamoto.duckdb"
    if not db_path.exists():
        db_path = work_dir / "db" / "niamoto.db"
    if not db_path.exists():
        logger.warning("Database not found, using default relation fields")
        return ref_field, match_field, 0.0

    def _quote(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    conn = None
    try:
        conn = duckdb.connect(str(db_path))
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
        table_lookup = {str(t[0]).lower(): str(t[0]) for t in tables}
        entity_table = next(
            (
                table_lookup[candidate.lower()]
                for candidate in (
                    f"entity_{reference_name}",
                    f"reference_{reference_name}",
                    reference_name,
                )
                if candidate.lower() in table_lookup
            ),
            None,
        )
        if not entity_table:
            return ref_field, match_field, 0.0

        entity_cols = conn.execute(f"DESCRIBE {_quote(entity_table)}").fetchall()
        matchable_entity_cols = [
            c[0]
            for c in entity_cols
            if "VARCHAR" in str(c[1]).upper() or "TEXT" in str(c[1]).upper()
        ]
        matchable_entity_cols.extend(
            [c[0] for c in entity_cols if str(c[0]).startswith("id")]
        )
        matchable_entity_cols = list(set(matchable_entity_cols))

        entity_values: dict[str, set[str]] = {}
        for col in matchable_entity_cols:
            try:
                quoted_col = _quote(col)
                result = conn.execute(
                    f"SELECT DISTINCT CAST({quoted_col} AS VARCHAR) "
                    f"FROM {_quote(entity_table)} LIMIT 1000"
                ).fetchall()
                entity_values[col] = {str(r[0]) for r in result if r[0] is not None}
            except Exception:
                continue

        with open(csv_path, "r", encoding="utf-8") as f:
            first_line = f.readline()
            delimiter = ";" if first_line.count(";") > first_line.count(",") else ","

        csv_values: dict[str, set[str]] = {}
        csv_candidates = [
            c
            for c in csv_columns
            if c in entity_candidates
            or "name" in c.lower()
            or "label" in c.lower()
            or c.lower().startswith("id_")
            or c.lower().endswith("_id")
            or c.lower().endswith("_code")
        ]

        for col in csv_candidates:
            try:
                quoted_col = _quote(col)
                result = conn.execute(
                    (
                        f"SELECT DISTINCT CAST({quoted_col} AS VARCHAR) "
                        "FROM read_csv_auto(?, delim=?, header=true) LIMIT 1000"
                    ),
                    [str(csv_path), delimiter],
                ).fetchall()
                csv_values[col] = {str(r[0]) for r in result if r[0] is not None}
            except Exception:
                continue

        best_score = 0.0
        best_ref_field = ref_field
        best_match_field = match_field

        for csv_col, csv_vals in csv_values.items():
            if not csv_vals:
                continue
            for entity_col, entity_vals in entity_values.items():
                if not entity_vals:
                    continue
                intersection = csv_vals & entity_vals
                if not intersection:
                    continue
                score = len(intersection) / len(csv_vals)
                csv_tokens = _column_tokens(csv_col)
                entity_tokens = _column_tokens(entity_col)
                if csv_tokens and entity_tokens:
                    score += 0.2 * (
                        len(csv_tokens & entity_tokens)
                        / len(csv_tokens | entity_tokens)
                    )
                if csv_col == "id" or entity_col == "id":
                    score -= 0.05
                if score > best_score:
                    best_score = score
                    best_ref_field = entity_col
                    best_match_field = csv_col

        if best_score > 0.5:
            logger.info(
                "Smart relation detection for %s: %s -> %s (score %.1f%%)",
                reference_name,
                best_match_field,
                best_ref_field,
                best_score * 100,
            )
            return best_ref_field, best_match_field, best_score

        logger.warning(
            "No good relation match found for %s (best score %.1f%%), using defaults",
            reference_name,
            best_score * 100,
        )
        return ref_field, match_field, best_score
    except Exception as e:
        logger.warning("Error during smart relation detection: %s", e)
        return ref_field, match_field, 0.0
    finally:
        if conn is not None:
            conn.close()


def find_best_stats_source_for_reference(
    work_dir: Path, reference_name: str
) -> dict[str, str] | None:
    """Find the best raw stats CSV for a reference based on actual joinability."""
    imports_dir = work_dir / "imports"
    if not imports_dir.exists():
        return None

    best: dict[str, str] | None = None
    best_score = 0.0

    for csv_path in sorted(imports_dir.glob("raw_*_stats.csv")):
        try:
            csv_columns = read_csv_columns(csv_path)
            ref_field, match_field, score = detect_relation_fields(
                work_dir, reference_name, csv_path, csv_columns
            )
        except Exception:
            continue

        if score <= best_score or score <= 0.5:
            continue

        source_name = csv_path.stem
        if source_name.startswith("raw_"):
            source_name = source_name[len("raw_") :]

        best = {
            "name": source_name,
            "data": f"imports/{csv_path.name}",
            "grouping": reference_name,
            "relation_plugin": "stats_loader",
            "key": "id",
            "ref_field": ref_field,
            "match_field": match_field,
        }
        best_score = score

    return best
