"""
Auto-scaffolding des configs transform.yml et export.yml après import.

Génère des entrées minimales pour chaque référence importée, afin que
l'utilisateur puisse naviguer dans l'interface sans erreur 404.

Idempotent : ne touche pas aux groupes déjà existants.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from niamoto.gui.api.services.templates.config_service import (
    find_export_group,
    find_transform_group,
    load_export_config,
    load_transform_config,
    save_export_config,
    save_transform_config,
)
from niamoto.gui.api.services.templates.relation_detection import (
    find_stats_sources_for_reference,
)

logger = logging.getLogger(__name__)


def build_relation_config(
    ref_name: str,
    kind: str,
    config: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Construit la config de relation pour un source transform.yml.

    Déduit le plugin (nested_set vs direct_reference) et les clés
    à partir du kind de la référence et de sa config d'import.

    Logique extraite de transformer_suggestions.py:build_relation_config.
    """
    key_field: Optional[str] = None
    ref_field = "id"

    if config and isinstance(config, dict):
        # Bloc relation explicite dans import.yml
        relation_config = config.get("relation", {})
        if relation_config:
            if relation_config.get("foreign_key"):
                key_field = relation_config["foreign_key"]
            if relation_config.get("reference_key"):
                ref_field = relation_config["reference_key"]

        # Références dérivées (ex: taxons extraits des occurrences)
        connector = config.get("connector", {})
        is_derived = connector.get("type") == "derived"
        if is_derived and not key_field:
            extraction = connector.get("extraction", {})
            if extraction.get("id_column"):
                key_field = extraction["id_column"]

        # schema.id_field en fallback si pas de relation explicite ni de dérivation
        if not key_field and not relation_config and not is_derived:
            schema = config.get("schema", {})
            if schema.get("id_field"):
                key_field = schema["id_field"]

    if kind == "hierarchical":
        if not key_field:
            return None
        return {
            "plugin": "nested_set",
            "key": key_field,
            "ref_key": ref_field,
            "fields": {
                "parent": "parent_id",
                "left": "lft",
                "right": "rght",
            },
        }
    else:
        if not key_field:
            return None
        return {
            "plugin": "direct_reference",
            "key": key_field,
            "ref_key": ref_field,
        }


def scaffold_configs(work_dir: Path) -> Tuple[bool, str]:
    """Génère des entrées minimales dans transform.yml et export.yml.

    Lit les références de import.yml et crée les groupes manquants.
    Idempotent : les groupes existants ne sont pas modifiés.

    Args:
        work_dir: Répertoire de travail contenant config/

    Returns:
        Tuple (changed, message) indiquant si des modifications ont été faites
    """
    import_path = work_dir / "config" / "import.yml"
    if not import_path.exists():
        return False, "import.yml introuvable"

    with open(import_path, "r", encoding="utf-8") as f:
        import_config = yaml.safe_load(f)

    if not import_config or "entities" not in import_config:
        return False, "import.yml vide ou sans entités"

    entities = import_config["entities"]
    references = entities.get("references", {}) or {}
    datasets = entities.get("datasets", {}) or {}

    if not references:
        return False, "Aucune référence dans import.yml"

    # Récupérer le premier dataset comme source de données par défaut
    first_dataset = next(iter(datasets), None)

    # Charger les configs existantes
    transform_groups = load_transform_config(work_dir)
    export_config = load_export_config(work_dir)

    # Normaliser : exports peut être None si le YAML contient "exports:" sans valeur
    if not export_config.get("exports"):
        export_config["exports"] = []

    transform_added: List[str] = []
    export_added: List[str] = []

    for ref_name, ref_config in references.items():
        ref_config = ref_config if isinstance(ref_config, dict) else {}
        kind = ref_config.get("kind", "generic")

        # --- Transform ---
        if not find_transform_group(transform_groups, ref_name):
            group = _build_transform_group(
                work_dir, ref_name, kind, ref_config, first_dataset
            )
            transform_groups.append(group)
            transform_added.append(ref_name)

        # --- Export ---
        if not find_export_group(export_config, ref_name):
            _add_export_group(export_config, ref_name)
            export_added.append(ref_name)

    # Sauvegarder si des changements ont été faits
    changed = bool(transform_added or export_added)
    if transform_added:
        save_transform_config(work_dir, transform_groups, create_backup=True)
    if export_added:
        save_export_config(work_dir, export_config, create_backup=True)

    parts = []
    if transform_added:
        parts.append(f"transform: {', '.join(transform_added)}")
    if export_added:
        parts.append(f"export: {', '.join(export_added)}")

    message = f"Groupes ajoutés — {'; '.join(parts)}" if parts else "Rien à ajouter"
    return changed, message


def _build_transform_group(
    work_dir: Path,
    ref_name: str,
    kind: str,
    ref_config: Dict[str, Any],
    first_dataset: Optional[str],
) -> Dict[str, Any]:
    """Construit un groupe transform minimal pour une référence."""
    import_path = work_dir / "config" / "import.yml"
    explicit_auxiliary_sources: List[Dict[str, Any]] = []
    if import_path.exists():
        with open(import_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}
        explicit_auxiliary_sources = [
            source
            for source in (import_config.get("auxiliary_sources", []) or [])
            if source.get("grouping") == ref_name
        ]

    stats_sources = (
        explicit_auxiliary_sources
        if explicit_auxiliary_sources
        else find_stats_sources_for_reference(work_dir, ref_name)
    )

    if kind == "spatial":
        if stats_sources:
            return {
                "group_by": ref_name,
                "sources": [
                    _build_stats_source_config(source) for source in stats_sources
                ],
                "widgets_data": {},
            }

        logger.debug(
            "Skipping default dataset relation for spatial reference '%s' because no explicit spatial key is available",
            ref_name,
        )
        return {
            "group_by": ref_name,
            "sources": [],
            "widgets_data": {},
        }

    connector = ref_config.get("connector", {}) if isinstance(ref_config, dict) else {}
    relation_config = (
        ref_config.get("relation", {}) if isinstance(ref_config, dict) else {}
    )
    data_name = (
        relation_config.get("dataset")
        or connector.get("source")
        or first_dataset
        or "occurrences"
    )
    source_name = data_name
    relation = build_relation_config(ref_name, kind, ref_config)

    sources: List[Dict[str, Any]] = []
    if relation:
        sources.append(
            {
                "name": source_name,
                "data": data_name,
                "grouping": ref_name,
                "relation": relation,
            }
        )
    elif kind != "spatial":
        logger.warning(
            "Skipping default transform relation for reference '%s' because no safe key could be inferred",
            ref_name,
        )

    return {
        "group_by": ref_name,
        "sources": sources
        + [_build_stats_source_config(source) for source in stats_sources],
        "widgets_data": {},
    }


def _build_stats_source_config(source: Dict[str, str]) -> Dict[str, Any]:
    """Convert a detected auxiliary stats source into transform.yml source config."""
    relation = source.get("relation", {})
    return {
        "name": source["name"],
        "data": source["data"],
        "grouping": source["grouping"],
        "relation": {
            "plugin": relation.get("plugin", source.get("relation_plugin")),
            "key": relation.get("key", source.get("key")),
            "ref_field": relation.get("ref_field", source.get("ref_field")),
            "match_field": relation.get("match_field", source.get("match_field")),
        },
    }


def _add_export_group(export_config: Dict[str, Any], ref_name: str) -> None:
    """Ajoute un groupe export minimal dans la config.

    Crée un export web_pages s'il n'existe pas, puis ajoute le groupe.
    """
    exports = export_config.setdefault("exports", [])

    # Trouver ou créer l'export web_pages
    web_export = None
    for export_entry in exports:
        if isinstance(export_entry, dict) and export_entry.get("name") == "web_pages":
            web_export = export_entry
            break

    if not web_export:
        web_export = {
            "name": "web_pages",
            "enabled": True,
            "exporter": "html_page_exporter",
            "groups": [],
        }
        exports.append(web_export)

    groups = web_export.setdefault("groups", [])
    groups.append(
        {
            "group_by": ref_name,
            "widgets": [],
        }
    )
