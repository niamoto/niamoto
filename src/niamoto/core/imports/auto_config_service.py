"""Core service for import auto-configuration orchestration.

This centralizes the UI-facing auto-config workflow so the HTTP router can stay
focused on transport concerns while the product behavior lives in core.
"""

from __future__ import annotations

import csv
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from niamoto.core.imports.auto_config_decision import (
    build_entity_decision,
    build_semantic_evidence,
)
from niamoto.core.domain_vocabulary import (
    find_taxon_identifier_column,
    find_taxon_name_column,
    infer_taxonomy_reference_name,
)
from niamoto.core.imports.auto_config_review import (
    build_auto_config_warnings,
    build_entity_review,
)
from niamoto.core.utils.column_detector import ColumnDetector, GeoPackageAnalyzer

logger = logging.getLogger(__name__)

CLASS_OBJECT_REQUIRED_COLUMNS = {"class_object", "class_name", "class_value"}


class AutoConfigService:
    """Build an import auto-configuration from a set of candidate files."""

    MAX_SAMPLE_ROWS = 1000
    ANALYSIS_SAMPLE_ROWS = 100

    def __init__(
        self,
        working_directory: Path,
        event_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.working_directory = Path(working_directory)
        self._working_directory_resolved = self.working_directory.resolve()
        self._event_sink = event_sink

    def _emit_event(
        self,
        kind: str,
        message: str,
        *,
        file: Optional[str] = None,
        entity: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an auto-config progress event when a sink is configured."""
        if not self._event_sink:
            return
        self._event_sink(
            {
                "kind": kind,
                "message": message,
                "timestamp": time.time(),
                "file": file,
                "entity": entity,
                "details": details or {},
            }
        )

    def _resolve_project_path(self, filepath: str) -> Path:
        """Resolve a project-relative path and reject paths outside the project."""
        resolved_path = (self.working_directory / filepath).resolve()
        try:
            resolved_path.relative_to(self._working_directory_resolved)
        except ValueError as exc:
            raise ValueError(f"Invalid path outside project: {filepath}") from exc
        return resolved_path

    def analyze_file(self, filepath: str) -> Dict[str, Any]:
        """Analyze a supported file from the working directory."""
        file_path = self._resolve_project_path(filepath)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        if file_path.suffix.lower() != ".csv":
            raise ValueError(f"Unsupported file type: {file_path.suffix}")
        return self.analyze_csv_file(file_path)

    def analyze_csv_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a CSV file without exposing internal sample rows."""
        analysis = self._analyze_csv_file(file_path, include_sample_rows=False)
        analysis.pop("_sample_rows", None)
        return analysis

    def _analyze_csv_file(
        self, file_path: Path, *, include_sample_rows: bool
    ) -> Dict[str, Any]:
        """Analyze a CSV file with smart detection."""
        columns, sample_rows, row_count = self._read_csv_columns_and_rows(
            file_path, max_rows=self.MAX_SAMPLE_ROWS
        )
        sample_data = sample_rows[: self.ANALYSIS_SAMPLE_ROWS]

        analysis = ColumnDetector.analyze_file_columns(columns, sample_data)
        analysis["filename"] = file_path.name
        analysis["filepath"] = str(file_path)
        analysis["row_count"] = row_count
        analysis["sample_size"] = len(sample_rows)
        if include_sample_rows:
            analysis["_sample_rows"] = sample_rows[: self.ANALYSIS_SAMPLE_ROWS]
        return analysis

    def detect_hierarchy(self, filepath: str) -> Dict[str, Any]:
        """Detect hierarchy-like structures in a CSV file."""
        file_path = self._resolve_project_path(filepath)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        if file_path.suffix.lower() != ".csv":
            raise ValueError("Only CSV files supported for hierarchy detection")

        columns, sample_data, _ = self._read_csv_columns_and_rows(
            file_path, max_rows=100, count_all_rows=False
        )
        hierarchy_info = ColumnDetector.detect_hierarchy_columns(columns, sample_data)

        if hierarchy_info["detected"] and sample_data:
            stats_per_level = {}
            for level, col_name in hierarchy_info["column_mapping"].items():
                values = [row.get(col_name) for row in sample_data if row.get(col_name)]
                unique_values = set(values)
                stats_per_level[level] = {
                    "column": col_name,
                    "unique_count": len(unique_values),
                    "sample_values": list(unique_values)[:5],
                }
            hierarchy_info["stats_per_level"] = stats_per_level

        return hierarchy_info

    def detect_relationships(
        self, source_file: str, target_files: List[str]
    ) -> Dict[str, Any]:
        """Detect relationships between a source CSV and target CSVs."""
        source_path = self._resolve_project_path(source_file)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_file}")

        source_columns, source_sample, _ = self._read_csv_columns_and_rows(
            source_path, max_rows=100, count_all_rows=False
        )
        source_entity_name = Path(source_file).stem
        all_relationships = []

        for target_file in target_files:
            target_path = self._resolve_project_path(target_file)
            if not target_path.exists():
                continue

            target_columns, target_sample, _ = self._read_csv_columns_and_rows(
                target_path, max_rows=100, count_all_rows=False
            )
            target_entity_name = Path(target_file).stem

            relationships = ColumnDetector.detect_relationships(
                source_columns,
                target_columns,
                source_sample,
                target_sample,
                source_entity_name,
                target_entity_name,
            )

            for relationship in relationships:
                relationship["target_file"] = target_file
                all_relationships.append(relationship)

        return {"relationships": all_relationships}

    def auto_configure(self, files: List[str]) -> Dict[str, Any]:
        """Analyze files and return auto-config output for the UI."""
        if not files:
            raise ValueError("No files provided")

        self._emit_event(
            "stage",
            f"Preparing analysis for {len(files)} file(s)",
            details={"file_count": len(files)},
        )

        csv_analyses: Dict[str, Dict[str, Any]] = {}
        gpkg_analyses: Dict[str, Dict[str, Any]] = {}
        tif_files: List[str] = []

        for filepath in files:
            file_path = self._resolve_project_path(filepath)

            if not file_path.exists():
                continue

            file_ext = file_path.suffix.lower()
            self._emit_event(
                "detail", f"Analyzing {Path(filepath).name}", file=filepath
            )
            if file_ext == ".csv":
                analysis = self._analyze_csv_file(file_path, include_sample_rows=True)
                analysis["relative_path"] = filepath
                csv_analyses[filepath] = analysis
                self._emit_event(
                    "finding",
                    f"Loaded {len(analysis.get('columns', []))} columns from {Path(filepath).name}",
                    file=filepath,
                    entity=Path(filepath).stem,
                    details={
                        "row_count": analysis.get("row_count", 0),
                        "column_count": len(analysis.get("columns", [])),
                    },
                )
                if analysis.get("hierarchy", {}).get("detected"):
                    hierarchy_levels = analysis["hierarchy"].get("levels", [])
                    self._emit_event(
                        "finding",
                        f"Detected hierarchy candidates in {Path(filepath).name}",
                        file=filepath,
                        entity=Path(filepath).stem,
                        details={"levels": hierarchy_levels},
                    )
            elif file_ext in [".gpkg", ".geojson"]:
                analysis = GeoPackageAnalyzer.analyze_gpkg(file_path)
                if "error" not in analysis:
                    analysis["relative_path"] = filepath
                    gpkg_analyses[filepath] = analysis
                    geometry_types = analysis.get("geometry_types", [])
                    self._emit_event(
                        "finding",
                        f"Detected spatial layer in {Path(filepath).name}",
                        file=filepath,
                        entity=Path(filepath).stem,
                        details={
                            "classification": analysis.get("classification"),
                            "geometry_types": geometry_types,
                        },
                    )
            elif file_ext in [".tif", ".tiff"]:
                tif_files.append(filepath)
                self._emit_event(
                    "finding",
                    f"Detected raster layer {Path(filepath).name}",
                    file=filepath,
                    entity=Path(filepath).stem,
                )

        if not csv_analyses and not gpkg_analyses and not tif_files:
            raise ValueError("No valid files to analyze")

        self._emit_event("stage", "Detecting relationships between files")
        referenced_by = self._detect_referenced_by(csv_analyses)

        decision_summary: Dict[str, Dict[str, Any]] = {}
        semantic_evidence: Dict[str, Dict[str, Any]] = {}

        self._emit_event("stage", "Classifying entities")
        for filepath, analysis in csv_analyses.items():
            entity_name = Path(filepath).stem
            decision = build_entity_decision(
                entity_name=entity_name,
                analysis=analysis,
                referenced_by=referenced_by,
                all_analyses=csv_analyses,
            )
            review = build_entity_review(decision=decision, analysis=analysis)
            decision_summary[entity_name] = {**decision, **review}
            semantic_evidence[entity_name] = build_semantic_evidence(
                analysis=analysis,
                decision=decision_summary[entity_name],
                referenced_by=referenced_by.get(entity_name, []),
            )
            self._emit_event(
                "finding",
                f"Classified {entity_name} as {decision_summary[entity_name]['final_entity_type']}",
                file=filepath,
                entity=entity_name,
                details={
                    "final_entity_type": decision_summary[entity_name][
                        "final_entity_type"
                    ],
                    "review_level": decision_summary[entity_name].get("review_level"),
                },
            )

        shapes_sources = []
        layers_info = []
        for filepath, analysis in gpkg_analyses.items():
            if analysis["classification"] == "shapes":
                name_field = (
                    analysis["name_field_candidates"][0]
                    if analysis["name_field_candidates"]
                    else "name"
                )
                shapes_sources.append(
                    {
                        "name": Path(filepath).stem.replace("_", " ").title(),
                        "path": filepath,
                        "layer": analysis.get("layer_analyzed"),
                        "name_field": name_field,
                    }
                )
            else:
                layers_info.append(
                    {
                        "name": Path(filepath).stem,
                        "type": "vector",
                        "format": "geopackage",
                        "path": filepath,
                        "description": (
                            f"{analysis['geometry_types'][0]} layer"
                            if analysis.get("geometry_types")
                            else "Vector layer"
                        ),
                    }
                )

        auxiliary_sources = self._detect_auxiliary_sources(
            csv_analyses=csv_analyses,
            decision_summary=decision_summary,
            has_shapes_reference=bool(shapes_sources),
        )

        for entity_name, auxiliary in auxiliary_sources.items():
            decision_summary[entity_name].update(
                {
                    "final_entity_type": "auxiliary_source",
                    "review_required": False,
                    "review_reasons": [],
                    "review_priority": "normal",
                    "auxiliary_target": auxiliary["grouping"],
                    "auxiliary_relation": auxiliary["relation"],
                }
            )
            semantic_evidence.setdefault(entity_name, {})["auxiliary_target"] = (
                auxiliary["grouping"]
            )
            semantic_evidence[entity_name]["auxiliary_relation"] = auxiliary["relation"]
            self._emit_event(
                "finding",
                f"Attached auxiliary source {entity_name} to {auxiliary['grouping']}",
                file=auxiliary["data"],
                entity=entity_name,
                details={"grouping": auxiliary["grouping"]},
            )

        references: Dict[str, Any] = {}
        datasets_to_create: Dict[str, Tuple[str, Dict[str, Any]]] = {}

        self._emit_event("stage", "Building import configuration")

        for filepath, analysis in csv_analyses.items():
            entity_name = Path(filepath).stem
            if entity_name in auxiliary_sources:
                continue

            entity_type = decision_summary[entity_name]["final_entity_type"]
            if entity_type == "hierarchical_reference":
                references[entity_name] = self._build_hierarchy_reference_config(
                    filepath, analysis, csv_analyses
                )
            elif entity_type == "reference":
                references[entity_name] = self._build_simple_reference_config(
                    filepath,
                    analysis,
                    referenced_by.get(entity_name),
                    decision_summary,
                )
            elif entity_type == "dataset":
                datasets_to_create[entity_name] = (filepath, analysis)

                if (
                    analysis.get("extract_hierarchy_as_reference", False)
                    and analysis["hierarchy"]["detected"]
                ):
                    ref_name = self._infer_reference_name(entity_name, analysis)
                    references[ref_name] = self._build_derived_hierarchy_reference(
                        entity_name, analysis
                    )

        if shapes_sources:
            references["shapes"] = self._build_shapes_reference(shapes_sources)

        datasets = {
            entity_name: self._build_dataset_config(filepath)
            for entity_name, (filepath, analysis) in datasets_to_create.items()
        }

        for tif_path in tif_files:
            layers_info.append(
                {
                    "name": Path(tif_path).stem,
                    "type": "raster",
                    "path": tif_path,
                    "description": f"Raster layer from {Path(tif_path).name}",
                }
            )

        all_confidences = [a["confidence"] for a in csv_analyses.values()]
        all_confidences.extend(a["confidence"] for a in gpkg_analyses.values())
        overall_confidence = (
            sum(all_confidences) / len(all_confidences) if all_confidences else 0.5
        )

        warnings = build_auto_config_warnings(
            decision_summary=decision_summary,
            overall_confidence=overall_confidence,
            has_references=bool(references),
        )
        detected_columns = {
            Path(filepath).stem: analysis.get("columns", [])
            for filepath, analysis in csv_analyses.items()
        }
        ml_predictions = {
            Path(filepath).stem: analysis.get("ml_predictions", [])
            for filepath, analysis in csv_analyses.items()
        }

        entities: Dict[str, Any] = {"datasets": datasets, "references": references}
        if layers_info:
            entities["metadata"] = {"layers": layers_info}

        return {
            "success": True,
            "entities": entities,
            "auxiliary_sources": list(auxiliary_sources.values()),
            "detected_columns": detected_columns,
            "ml_predictions": ml_predictions,
            "decision_summary": decision_summary,
            "semantic_evidence": semantic_evidence,
            "confidence": overall_confidence,
            "warnings": warnings,
        }

    def _detect_auxiliary_sources(
        self,
        csv_analyses: Dict[str, Dict[str, Any]],
        decision_summary: Dict[str, Dict[str, Any]],
        *,
        has_shapes_reference: bool,
    ) -> Dict[str, Dict[str, Any]]:
        auxiliary_sources: Dict[str, Dict[str, Any]] = {}
        reference_candidates = {
            Path(filepath).stem
            for filepath in csv_analyses
            if decision_summary.get(Path(filepath).stem, {}).get("final_entity_type")
            in {"reference", "hierarchical_reference"}
        }

        for filepath, analysis in csv_analyses.items():
            entity_name = Path(filepath).stem
            if not self._is_auxiliary_stats_candidate(analysis):
                continue

            source_config = self._build_auxiliary_source_config(
                filepath=filepath,
                entity_name=entity_name,
                analysis=analysis,
                csv_analyses=csv_analyses,
                reference_candidates=reference_candidates,
                has_shapes_reference=has_shapes_reference,
            )
            if source_config:
                auxiliary_sources[entity_name] = source_config

        logger.debug(
            "Auto-config detected %d auxiliary source(s)", len(auxiliary_sources)
        )
        return auxiliary_sources

    def _detect_referenced_by(
        self, csv_analyses: Dict[str, Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        referenced_by: Dict[str, List[Dict[str, Any]]] = {}

        for filepath, analysis in csv_analyses.items():
            entity_name = Path(filepath).stem
            for other_filepath, other_analysis in csv_analyses.items():
                if filepath == other_filepath:
                    continue

                other_name = Path(other_filepath).stem
                relationships = ColumnDetector.detect_relationships(
                    other_analysis["columns"],
                    analysis["columns"],
                    source_sample=other_analysis.get("_sample_rows"),
                    target_sample=analysis.get("_sample_rows"),
                    source_entity_name=other_name,
                    target_entity_name=entity_name,
                )

                high_confidence_rels = [
                    rel for rel in relationships if rel["confidence"] >= 0.5
                ]
                if not high_confidence_rels:
                    continue

                best_rel = None
                for rel in high_confidence_rels:
                    source_field_lower = rel["source_field"].lower()
                    target_field_lower = rel["target_field"].lower()
                    is_id_match = (
                        "id" in source_field_lower or "id" in target_field_lower
                    ) and (
                        entity_name.lower() in source_field_lower
                        or entity_name.lower() in target_field_lower
                    )
                    if is_id_match:
                        best_rel = rel
                        break

                if not best_rel:
                    semantic_rels = [
                        rel
                        for rel in high_confidence_rels
                        if rel.get("match_type") == "semantic_context"
                    ]
                    best_rel = (
                        max(semantic_rels, key=lambda rel: rel["confidence"])
                        if semantic_rels
                        else max(
                            high_confidence_rels, key=lambda rel: rel["confidence"]
                        )
                    )

                referenced_by.setdefault(entity_name, []).append(
                    {
                        "from": other_name,
                        "field": best_rel["source_field"],
                        "target_field": best_rel["target_field"],
                        "confidence": best_rel["confidence"],
                        "match_type": best_rel.get("match_type"),
                    }
                )
                self._emit_event(
                    "finding",
                    (
                        f"Detected relationship {other_name}.{best_rel['source_field']} "
                        f"-> {entity_name}.{best_rel['target_field']}"
                    ),
                    file=other_filepath,
                    entity=other_name,
                    details={
                        "target_entity": entity_name,
                        "source_field": best_rel["source_field"],
                        "target_field": best_rel["target_field"],
                        "confidence": best_rel["confidence"],
                    },
                )

        logger.debug(
            "Auto-config relationship scan detected references for %d entities",
            len(referenced_by),
        )
        return referenced_by

    def _read_csv_columns_and_rows(
        self, file_path: Path, max_rows: int, *, count_all_rows: bool = True
    ) -> Tuple[List[str], List[Dict[str, Any]], int]:
        """Read CSV header and sample rows, optionally counting the full file length."""
        with open(file_path, "r", encoding="utf-8") as f:
            first_line = f.readline()
            delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
            f.seek(0)
            reader = csv.DictReader(f, delimiter=delimiter)
            columns = reader.fieldnames or []

            rows: List[Dict[str, Any]] = []
            row_count = 0
            for row in reader:
                if row_count < max_rows:
                    rows.append(row)
                    row_count += 1
                elif not count_all_rows:
                    break
                else:
                    row_count += 1

        return columns, rows, row_count

    def _is_auxiliary_stats_candidate(self, analysis: Dict[str, Any]) -> bool:
        columns = {column.lower() for column in analysis.get("columns", [])}
        return CLASS_OBJECT_REQUIRED_COLUMNS.issubset(columns)

    def _build_auxiliary_source_config(
        self,
        *,
        filepath: str,
        entity_name: str,
        analysis: Dict[str, Any],
        csv_analyses: Dict[str, Dict[str, Any]],
        reference_candidates: set[str],
        has_shapes_reference: bool,
    ) -> Optional[Dict[str, Any]]:
        best_match = self._find_auxiliary_reference_match(
            entity_name=entity_name,
            analysis=analysis,
            csv_analyses=csv_analyses,
            reference_candidates=reference_candidates,
        )
        if best_match:
            return {
                "name": self._auxiliary_source_name(entity_name),
                "data": filepath,
                "grouping": best_match["target"],
                "relation": {
                    "plugin": "stats_loader",
                    "key": "id",
                    "ref_field": best_match["target_field"],
                    "match_field": best_match["source_field"],
                },
                "source_entity": entity_name,
            }

        if has_shapes_reference:
            label_field = self._find_auxiliary_label_field(analysis)
            if label_field:
                return {
                    "name": self._auxiliary_source_name(entity_name),
                    "data": filepath,
                    "grouping": "shapes",
                    "relation": {
                        "plugin": "stats_loader",
                        "key": "id",
                        "ref_field": "name",
                        "match_field": label_field,
                    },
                    "source_entity": entity_name,
                }

        return None

    def _find_auxiliary_reference_match(
        self,
        *,
        entity_name: str,
        analysis: Dict[str, Any],
        csv_analyses: Dict[str, Dict[str, Any]],
        reference_candidates: set[str],
    ) -> Optional[Dict[str, Any]]:
        best_match: Optional[Dict[str, Any]] = None

        for other_filepath, other_analysis in csv_analyses.items():
            target_name = Path(other_filepath).stem
            if target_name == entity_name or target_name not in reference_candidates:
                continue

            relationships = ColumnDetector.detect_relationships(
                analysis.get("columns", []),
                other_analysis.get("columns", []),
                source_sample=analysis.get("_sample_rows"),
                target_sample=other_analysis.get("_sample_rows"),
                source_entity_name=entity_name,
                target_entity_name=target_name,
            )
            for relationship in relationships:
                confidence = float(relationship.get("confidence", 0.0) or 0.0)
                source_field = str(relationship.get("source_field", ""))
                target_field = str(relationship.get("target_field", ""))

                if confidence < 0.75:
                    continue
                if target_field == "id" and source_field != "id":
                    continue

                candidate = {
                    "target": target_name,
                    "source_field": source_field,
                    "target_field": target_field,
                    "confidence": confidence,
                    "match_type": relationship.get("match_type"),
                }
                if not best_match or self._auxiliary_match_priority(
                    candidate
                ) > self._auxiliary_match_priority(best_match):
                    best_match = candidate

        return best_match

    def _auxiliary_match_priority(
        self, candidate: Dict[str, Any]
    ) -> tuple[float, int, int]:
        """Prefer entity-specific auxiliary joins over generic id/id overlaps."""
        target_name = str(candidate.get("target", "")).lower()
        target_tokens = {
            part.rstrip("s")
            for part in target_name.split("_")
            if part and part not in {"raw", "entity", "dataset"}
        }
        source_field = str(candidate.get("source_field", "")).lower()
        target_field = str(candidate.get("target_field", "")).lower()
        match_type = str(candidate.get("match_type", ""))

        mentions_target = any(
            token and (token in source_field or token in target_field)
            for token in target_tokens
        )
        generic_id_match = source_field == "id" and target_field == "id"
        match_type_rank = {
            "semantic_context": 3,
            "exact_match": 2,
            "name_similarity": 1,
        }.get(match_type, 0)

        return (
            float(candidate.get("confidence", 0.0) or 0.0),
            int(mentions_target) - int(generic_id_match),
            match_type_rank,
        )

    def _find_auxiliary_label_field(self, analysis: Dict[str, Any]) -> Optional[str]:
        columns = analysis.get("columns", [])
        lowered = {column.lower(): column for column in columns}
        for candidate in ("label", "name"):
            if candidate in lowered:
                return lowered[candidate]
        name_columns = analysis.get("name_columns", [])
        return name_columns[0] if name_columns else None

    def _auxiliary_source_name(self, entity_name: str) -> str:
        return entity_name[4:] if entity_name.startswith("raw_") else entity_name

    def _build_hierarchy_reference_config(
        self,
        filepath: str,
        analysis: Dict[str, Any],
        all_analyses: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        hierarchy = analysis["hierarchy"]
        is_derived = False
        source_dataset = None

        for other_filepath, other_analysis in all_analyses.items():
            if other_filepath == filepath:
                continue
            other_columns = set(other_analysis.get("columns", []))
            hierarchy_columns = set(hierarchy["column_mapping"].values())
            if hierarchy_columns.issubset(other_columns):
                is_derived = True
                source_dataset = Path(other_filepath).stem
                break

        if is_derived and source_dataset:
            levels_config = [
                {"name": level, "column": hierarchy["column_mapping"][level]}
                for level in hierarchy["levels"]
                if level in hierarchy["column_mapping"]
            ]
            return {
                "kind": "hierarchical",
                "connector": {
                    "type": "derived",
                    "source": source_dataset,
                    "extraction": {
                        "levels": levels_config,
                        "id_strategy": "hash",
                        "incomplete_rows": "skip",
                    },
                },
                "hierarchy": {
                    "strategy": "adjacency_list",
                    "levels": hierarchy["levels"],
                },
                "schema": {"id_field": "id", "fields": []},
            }

        id_column = analysis["id_columns"][0] if analysis["id_columns"] else "id"
        return {
            "kind": "hierarchical",
            "connector": {"type": "file", "format": "csv", "path": filepath},
            "hierarchy": {
                "strategy": "adjacency_list",
                "levels": hierarchy["levels"],
            },
            "schema": {"id_field": id_column, "fields": []},
        }

    def _build_simple_reference_config(
        self,
        filepath: str,
        analysis: Dict[str, Any],
        relation_info: Optional[List[Dict[str, Any]]] = None,
        decision_summary: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        id_column = analysis["id_columns"][0] if analysis["id_columns"] else "id"
        name_columns = analysis.get("name_columns", [])
        name_column = name_columns[0] if name_columns else None

        config = {
            "connector": {"type": "file", "format": "csv", "path": filepath},
            "schema": {"id_field": id_column, "fields": []},
        }

        if analysis["geometry_columns"]:
            config["schema"]["fields"].append(
                {"name": analysis["geometry_columns"][0], "type": "geometry"}
            )

        if relation_info:
            best_relation = self._select_reference_relation(
                relation_info,
                decision_summary or {},
            )
            reference_key = (
                best_relation.get("target_field") or name_column or id_column
            )
            config["relation"] = {
                "dataset": best_relation["from"],
                "foreign_key": best_relation["field"],
                "reference_key": reference_key,
            }

        return config

    def _select_reference_relation(
        self,
        relation_info: List[Dict[str, Any]],
        decision_summary: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Pick the relation that should define the main reference link.

        Auxiliary sources are valid transform inputs, but they must not replace
        the primary dataset relationship stored in import.yml.
        """

        def _priority(item: Dict[str, Any]) -> tuple[int, float]:
            source_name = str(item.get("from", ""))
            source_type = (
                decision_summary.get(source_name, {}).get("final_entity_type")
                if decision_summary
                else None
            )
            type_rank = {
                "dataset": 3,
                "reference": 2,
                "hierarchical_reference": 2,
                "auxiliary_source": 0,
            }.get(str(source_type), 1)
            confidence = float(item.get("confidence", 0.0) or 0.0)
            return (type_rank, confidence)

        return max(relation_info, key=_priority)

    def _build_shapes_reference(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "kind": "spatial",
            "description": "Geographic reference features for spatial analysis",
            "connector": {"type": "file_multi_feature", "sources": sources},
            "schema": {
                "fields": [
                    {
                        "name": "name",
                        "type": "string",
                        "description": "Feature name from source file",
                    },
                    {
                        "name": "location",
                        "type": "geometry",
                        "description": "Geometry in WKT format",
                    },
                    {
                        "name": "entity_type",
                        "type": "string",
                        "description": "Source type",
                    },
                ]
            },
        }

    def _build_dataset_config(
        self,
        filepath: str,
    ) -> Dict[str, Any]:
        return {"connector": {"type": "file", "format": "csv", "path": filepath}}

    def _infer_reference_name(self, dataset_name: str, analysis: Dict[str, Any]) -> str:
        levels = analysis.get("hierarchy", {}).get("levels", [])
        return infer_taxonomy_reference_name(dataset_name, levels)

    def _build_derived_hierarchy_reference(
        self,
        source_dataset: str,
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        hierarchy = analysis["hierarchy"]
        levels_config = [
            {"name": level, "column": hierarchy["column_mapping"][level]}
            for level in hierarchy["levels"]
            if level in hierarchy["column_mapping"]
        ]

        id_col = find_taxon_identifier_column(analysis["columns"])
        name_col = find_taxon_name_column(analysis["columns"])

        if not name_col and analysis["name_columns"]:
            name_col = analysis["name_columns"][0]

        return {
            "kind": "hierarchical",
            "description": f"Taxonomic hierarchy extracted from {source_dataset}",
            "connector": {
                "type": "derived",
                "source": source_dataset,
                "extraction": {
                    "levels": levels_config,
                    "id_column": id_col,
                    "name_column": name_col,
                    "id_strategy": "hash",
                    "incomplete_rows": "skip",
                },
            },
            "hierarchy": {
                "strategy": "adjacency_list",
                "levels": hierarchy["levels"],
            },
            "schema": {"id_field": "id", "fields": []},
        }
