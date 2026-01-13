"""
Helper functions for templates API.

These functions handle configuration loading and reference information
extraction from import.yml and transform.yml files.
"""

import logging
from pathlib import Path
from typing import Any, Dict

import yaml
from fastapi import HTTPException

from niamoto.gui.api.context import get_working_directory

logger = logging.getLogger(__name__)


def load_import_config(work_dir: Path) -> Dict[str, Any]:
    """Load and parse import.yml configuration."""
    import_path = work_dir / "config" / "import.yml"
    if not import_path.exists():
        raise HTTPException(
            status_code=404,
            detail="import.yml not found. Please configure your import first.",
        )

    with open(import_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_reference_info(
    ref_name: str, ref_config: Dict[str, Any], import_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Build reference info dict from config.

    Args:
        ref_name: Name of the reference
        ref_config: Reference configuration from import.yml
        import_config: Full import.yml configuration

    Returns:
        Dict with reference information
    """
    kind = ref_config.get("kind")  # hierarchical, spatial, or None
    hierarchy = ref_config.get("hierarchy", {})
    levels = hierarchy.get("levels", [])

    connector = ref_config.get("connector", {})
    source_dataset = connector.get("source", "occurrences")

    # Get level to column mapping (for hierarchical references)
    level_columns = {}
    extraction = connector.get("extraction", {})
    for level_info in extraction.get("levels", []):
        level_columns[level_info["name"]] = level_info.get("column", level_info["name"])

    # Get schema info
    schema = ref_config.get("schema", {})
    id_field = schema.get("id_field", "id")

    # Get relation info from import.yml (for flat references like plots)
    # This links the reference to occurrences via foreign_key/reference_key
    relation_config = ref_config.get("relation", {})
    relation = {}
    if relation_config:
        # Convert import.yml format to transform.yml compatible format
        # import.yml: { dataset: "occurrences", foreign_key: "plot_name", reference_key: "plot" }
        # transform.yml: { plugin: "direct_reference", key: "plot_name", ref_field: "plot" }
        relation = {
            "plugin": "direct_reference",
            "key": relation_config.get("foreign_key"),  # Column in occurrences
            "ref_field": relation_config.get("reference_key"),  # Column in reference
        }

    return {
        "reference_name": ref_name,
        "levels": levels,
        "source_dataset": source_dataset,
        "level_columns": level_columns,
        "kind": kind,
        "id_field": id_field,
        "is_hierarchical_grouping": kind == "hierarchical",
        "relation": relation,
    }


def get_hierarchy_info(
    import_config: Dict[str, Any], reference_name: str = None
) -> Dict[str, Any]:
    """Extract reference information from import.yml and transform.yml.

    This function is generic and works with:
    - Hierarchical references (taxons with nested_set)
    - Flat references (plots without hierarchy)
    - Spatial references (shapes)
    - Plots with nested_set hierarchy (from transform.yml)

    Args:
        import_config: Loaded import.yml configuration
        reference_name: Specific reference to get info for (e.g., 'plots', 'shapes').
                       If None, returns the first hierarchical reference.

    Returns dict with:
    - reference_name: Name of the reference (e.g., 'taxons', 'plots')
    - levels: List of hierarchy levels (empty for flat references)
    - source_dataset: Name of source dataset (e.g., 'occurrences')
    - level_columns: Mapping of level name to column name
    - kind: Type of reference ('hierarchical', 'spatial', or None for flat)
    - is_hierarchical_grouping: True if transform.yml uses nested_set for this reference
    """
    references = import_config.get("entities", {}).get("references", {})

    # If a specific reference is requested, look for it
    if reference_name:
        # First, try to get relation info from transform.yml (needed for filtering occurrences)
        relation = {}
        source_dataset = "occurrences"
        is_hierarchical_grouping = False
        transform_config = []

        work_dir = get_working_directory()
        if work_dir:
            transform_path = Path(work_dir) / "config" / "transform.yml"
            if transform_path.exists():
                try:
                    with open(transform_path, "r", encoding="utf-8") as f:
                        transform_config = yaml.safe_load(f) or []

                    # Find the group matching the reference_name
                    for group in transform_config:
                        if group.get("group_by") == reference_name:
                            sources = group.get("sources", [])
                            # Look for a database dataset source (not a CSV file path)
                            for source in sources:
                                data = source.get("data", "occurrences")
                                # Skip CSV file paths (class_objects), use only database datasets
                                if "/" in data or data.endswith(".csv"):
                                    continue
                                source_dataset = data
                                relation = source.get("relation", {})
                                relation_plugin = relation.get("plugin")
                                is_hierarchical_grouping = (
                                    relation_plugin == "nested_set"
                                )
                                break
                            break
                except Exception as e:
                    logger.warning(f"Error reading transform.yml: {e}")

        # Now get reference config from import.yml
        ref_config = references.get(reference_name)
        if ref_config:
            info = build_reference_info(reference_name, ref_config, import_config)
            # Override with transform.yml info (but keep import.yml relation if transform.yml has none)
            info["source_dataset"] = source_dataset
            if relation:  # Only override if transform.yml has relation info
                info["relation"] = relation
            # Note: info["relation"] is already set from import.yml by build_reference_info
            info["is_hierarchical_grouping"] = is_hierarchical_grouping
            return info

        # Reference not found by exact name, maybe it's a group_by alias
        # Check if we found it in transform.yml with a different grouping name
        if relation:
            # Try to find the actual reference from grouping field in transform.yml
            for group in transform_config:
                if group.get("group_by") == reference_name:
                    sources = group.get("sources", [])
                    if sources:
                        grouping = sources[0].get("grouping", reference_name)
                        # Look for the reference by grouping name
                        for ref_name, ref_cfg in references.items():
                            if ref_name == grouping:
                                info = build_reference_info(
                                    ref_name, ref_cfg, import_config
                                )
                                info["source_dataset"] = source_dataset
                                info["is_hierarchical_grouping"] = (
                                    is_hierarchical_grouping
                                )
                                info["relation"] = relation
                                return info
                    break

            # Reference not in import.yml, create minimal info
            return {
                "reference_name": reference_name,
                "levels": [],
                "source_dataset": source_dataset,
                "level_columns": {},
                "kind": None,
                "is_hierarchical_grouping": is_hierarchical_grouping,
                "relation": relation,
            }

    # Fallback: return first hierarchical reference (original behavior)
    for ref_name, ref_config in references.items():
        if ref_config.get("kind") == "hierarchical":
            return build_reference_info(ref_name, ref_config, import_config)

    # No hierarchical reference found, return first reference if any
    if references:
        first_ref_name = next(iter(references))
        return build_reference_info(
            first_ref_name, references[first_ref_name], import_config
        )

    raise HTTPException(
        status_code=400,
        detail="No reference found in import.yml",
    )
