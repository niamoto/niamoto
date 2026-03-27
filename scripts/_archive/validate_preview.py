#!/usr/bin/env python
"""
Validation des previews contre l'instance finalisée.

Compare les transformations du système de preview automatique avec
les résultats pré-calculés de l'instance finalisée test-instance/niamoto-nc.

Focus: Distributions (binned_distribution, categorical_distribution)
Tolérance: 5% sur les proportions (strict)
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Configuration
INSTANCE_PATH = Path("test-instance/niamoto-nc")
TOLERANCE = 5.0  # 5% tolérance sur les proportions
SAMPLE_LIMIT = None  # None = toutes les données (comme l'interface)

# Myrtaceae - famille avec le plus d'occurrences (sélectionnée par le preview)
MYRTACEAE_TAXON_ID = 3802854842
MYRTACEAE_FAMILY_NAME = "Myrtaceae"

# Mapping des widgets finalisés vers les template IDs du preview
# Format template_id: {column}_{transformer}_{widget}
VALIDATION_TARGETS = {
    "dbh_distribution": {
        "template_id": "dbh_binned_distribution_bar_plot",
        "transformer": "binned_distribution",
        "widget": "bar_plot",
        "column": "dbh",
        "type": "binned",
        "config": {
            "source": "occurrences",
            "field": "dbh",
            "bins": [10, 20, 30, 40, 50, 75, 100, 200, 300, 400, 500],
            "include_percentages": True,
        },
    },
    "elevation_distribution": {
        "template_id": "elevation_binned_distribution_bar_plot",
        "transformer": "binned_distribution",
        "widget": "bar_plot",
        "column": "elevation",
        "type": "binned",
        "config": {
            "source": "occurrences",
            "field": "elevation",
            "bins": [
                100,
                200,
                300,
                400,
                500,
                600,
                700,
                800,
                900,
                1000,
                1100,
                1200,
                1700,
            ],
            "include_percentages": True,
        },
    },
    "holdridge_distribution": {
        "template_id": "holdridge_categorical_distribution_donut_chart",
        "transformer": "categorical_distribution",
        "widget": "donut_chart",
        "column": "holdridge",
        "type": "categorical",
        "config": {
            "source": "occurrences",
            "field": "holdridge",
            "categories": [1, 2, 3],
            "labels": ["Sec", "Humide", "Très humide"],
            "include_percentages": True,
        },
    },
    "strata_distribution": {
        "template_id": "strata_categorical_distribution_donut_chart",
        "transformer": "categorical_distribution",
        "widget": "donut_chart",
        "column": "strata",
        "type": "categorical",
        "config": {
            "source": "occurrences",
            "field": "strata",
            "categories": [1, 2, 3, 4],
            "labels": ["Sous-bois", "Sous-Canopée", "Canopée", "Emergent"],
        },
    },
}


@dataclass
class ValidationResult:
    """Résultat de validation d'un widget."""

    widget_name: str
    passed: bool
    max_diff: float
    errors: List[str]
    preview_proportions: List[float]
    finalized_proportions: List[float]
    bins_or_categories: List[Any]


def load_finalized_data(taxon_id: int) -> Dict[str, Any]:
    """Charge les données JSON exportées pour un taxon."""
    json_path = INSTANCE_PATH / "exports" / "api" / "taxons" / f"{taxon_id}.json"
    if not json_path.exists():
        raise FileNotFoundError(f"Fichier exporté non trouvé: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_sample_data(
    family_name: str, limit: Optional[int] = SAMPLE_LIMIT
) -> pd.DataFrame:
    """Charge les données d'échantillon pour une famille."""
    from niamoto.common.database import Database

    db_path = INSTANCE_PATH / "db" / "niamoto.duckdb"
    db = Database(str(db_path), read_only=True)

    try:
        # Chercher la table des occurrences
        table_name = None
        for name in ["dataset_occurrences", "entity_occurrences", "occurrences"]:
            if db.has_table(name):
                table_name = name
                break

        if not table_name:
            raise RuntimeError("Table occurrences non trouvée")

        # Charger les données pour la famille
        query = f"""
            SELECT *
            FROM {table_name}
            WHERE "family" = '{family_name}'
        """
        # Ajouter échantillonnage aléatoire si limite spécifiée
        if limit:
            query += f" ORDER BY RANDOM() LIMIT {limit}"
        return pd.read_sql(query, db.engine)
    finally:
        db.close_db_session()


def execute_transformer(
    data: pd.DataFrame, transformer_name: str, config: Dict[str, Any]
) -> Dict[str, Any]:
    """Exécute un transformer sur les données."""
    from niamoto.common.database import Database
    from niamoto.core.plugins.base import PluginType
    from niamoto.core.plugins.registry import PluginRegistry

    # Import des plugins
    if transformer_name == "binned_distribution":
        from niamoto.core.plugins.transformers.distribution import (
            binned_distribution,  # noqa: F401
        )
    elif transformer_name == "categorical_distribution":
        from niamoto.core.plugins.transformers.distribution import (
            categorical_distribution,  # noqa: F401
        )

    db_path = INSTANCE_PATH / "db" / "niamoto.duckdb"
    db = Database(str(db_path), read_only=True)

    try:
        plugin_class = PluginRegistry.get_plugin(
            transformer_name, PluginType.TRANSFORMER
        )
        plugin_instance = plugin_class(db=db)

        full_config = {"plugin": transformer_name, "params": config}
        return plugin_instance.transform(data, full_config)
    finally:
        db.close_db_session()


def calculate_proportions(counts: List[int]) -> List[float]:
    """Calcule les proportions à partir des comptages."""
    total = sum(counts) or 1
    return [(c / total) * 100 for c in counts]


def compare_distributions(
    preview_data: Dict[str, Any],
    finalized_data: Dict[str, Any],
    widget_name: str,
    dist_type: str,
    tolerance: float = TOLERANCE,
) -> ValidationResult:
    """
    Compare deux distributions avec tolérance sur les proportions.

    Args:
        preview_data: Données issues du preview (échantillon 500 lignes)
        finalized_data: Données de l'instance finalisée (toutes les données)
        widget_name: Nom du widget pour le rapport
        dist_type: Type de distribution ('binned' ou 'categorical')
        tolerance: Tolérance en % sur les écarts de proportions

    Returns:
        ValidationResult avec le statut et les détails
    """
    errors = []

    # 1. Validation structurelle
    if dist_type == "binned":
        preview_bins = preview_data.get("bins", [])
        final_bins = finalized_data.get("bins", [])
        bins_label = "bins"
    else:
        preview_bins = preview_data.get("categories", [])
        final_bins = finalized_data.get("categories", [])
        bins_label = "categories"

    if preview_bins != final_bins:
        errors.append(
            f"Structure {bins_label} différente: preview={preview_bins}, final={final_bins}"
        )

    # 2. Validation des proportions
    preview_counts = preview_data.get("counts", [])
    final_counts = finalized_data.get("counts", [])

    if len(preview_counts) != len(final_counts):
        errors.append(
            f"Nombre de bins différent: preview={len(preview_counts)}, final={len(final_counts)}"
        )
        return ValidationResult(
            widget_name=widget_name,
            passed=False,
            max_diff=100.0,
            errors=errors,
            preview_proportions=[],
            finalized_proportions=[],
            bins_or_categories=final_bins,
        )

    preview_props = calculate_proportions(preview_counts)
    final_props = calculate_proportions(final_counts)

    max_diff = 0.0
    for i, (p, f) in enumerate(zip(preview_props, final_props)):
        diff = abs(p - f)
        max_diff = max(max_diff, diff)

        if diff > tolerance:
            bin_label = preview_bins[i] if i < len(preview_bins) else f"Bin {i}"
            errors.append(
                f"Bin '{bin_label}': preview={p:.1f}%, final={f:.1f}% (écart={diff:.1f}%)"
            )

    return ValidationResult(
        widget_name=widget_name,
        passed=len(errors) == 0,
        max_diff=max_diff,
        errors=errors,
        preview_proportions=preview_props,
        finalized_proportions=final_props,
        bins_or_categories=preview_bins if preview_bins else final_bins,
    )


def generate_report(
    results: List[ValidationResult], console: Console, sample_size: int
) -> None:
    """Génère le rapport de validation avec rich."""
    # En-tête
    sample_info = (
        f"{SAMPLE_LIMIT} lignes" if SAMPLE_LIMIT else f"Toutes ({sample_size} lignes)"
    )
    console.print()
    console.print(
        Panel(
            f"[bold white]Validation Preview vs Instance Finalisée[/bold white]\n"
            f"[dim]Famille: {MYRTACEAE_FAMILY_NAME} | "
            f"Échantillon: {sample_info} | "
            f"Tolérance: {TOLERANCE}%[/dim]",
            style="blue",
        )
    )
    console.print()

    # Tableau récapitulatif
    table = Table(
        title="Résultats par Widget", show_header=True, header_style="bold cyan"
    )
    table.add_column("Widget", style="white", width=25)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Écart Max", justify="right", width=12)
    table.add_column("Détails", width=40)

    passed_count = 0
    for result in results:
        if result.passed:
            status = "[green]✓ PASS[/green]"
            passed_count += 1
            details = f"[dim]Proportions OK (max {result.max_diff:.1f}%)[/dim]"
        elif result.max_diff <= TOLERANCE * 1.5:  # Warning si proche de la tolérance
            status = "[yellow]⚠ WARN[/yellow]"
            details = f"[yellow]{len(result.errors)} écart(s) > {TOLERANCE}%[/yellow]"
        else:
            status = "[red]✗ FAIL[/red]"
            details = f"[red]{len(result.errors)} écart(s) significatifs[/red]"

        table.add_row(result.widget_name, status, f"{result.max_diff:.1f}%", details)

    console.print(table)
    console.print()

    # Détails des échecs
    failed_results = [r for r in results if not r.passed]
    if failed_results:
        console.print("[bold yellow]Détails des écarts:[/bold yellow]")
        for result in failed_results:
            console.print(f"\n[bold]{result.widget_name}[/bold]:")
            for error in result.errors[:5]:  # Limiter à 5 erreurs par widget
                console.print(f"  • {error}")
            if len(result.errors) > 5:
                console.print(
                    f"  [dim]... et {len(result.errors) - 5} autres écarts[/dim]"
                )
        console.print()

    # Tableau de comparaison des proportions pour chaque widget
    console.print("[bold]Comparaison des Proportions:[/bold]")
    for result in results:
        comp_table = Table(
            title=result.widget_name, show_header=True, header_style="bold"
        )
        comp_table.add_column("Bin/Cat", style="cyan", width=15)
        comp_table.add_column("Preview %", justify="right", width=12)
        comp_table.add_column("Final %", justify="right", width=12)
        comp_table.add_column("Écart", justify="right", width=10)

        for i, bin_val in enumerate(result.bins_or_categories):
            if i < len(result.preview_proportions) and i < len(
                result.finalized_proportions
            ):
                prev_p = result.preview_proportions[i]
                final_p = result.finalized_proportions[i]
                diff = abs(prev_p - final_p)

                diff_style = "[green]" if diff <= TOLERANCE else "[red]"
                comp_table.add_row(
                    str(bin_val),
                    f"{prev_p:.1f}",
                    f"{final_p:.1f}",
                    f"{diff_style}{diff:.1f}[/]",
                )

        console.print(comp_table)
        console.print()

    # Résumé final
    total = len(results)
    summary_style = (
        "green" if passed_count == total else "yellow" if passed_count > 0 else "red"
    )
    console.print(
        Panel(
            f"[bold]Résultat: {passed_count}/{total} validations passées[/bold]",
            style=summary_style,
        )
    )


def main():
    """Point d'entrée principal."""
    console = Console()

    console.print("[bold blue]Chargement des données...[/bold blue]")

    # 1. Charger les données finalisées
    try:
        finalized = load_finalized_data(MYRTACEAE_TAXON_ID)
        console.print(
            f"  ✓ Données finalisées chargées (taxon_id={MYRTACEAE_TAXON_ID})"
        )
    except FileNotFoundError as e:
        console.print(f"[red]Erreur: {e}[/red]")
        return 1

    # 2. Charger l'échantillon de données
    try:
        sample_data = load_sample_data(MYRTACEAE_FAMILY_NAME, SAMPLE_LIMIT)
        console.print(f"  ✓ Échantillon chargé ({len(sample_data)} lignes)")
    except Exception as e:
        console.print(f"[red]Erreur lors du chargement de l'échantillon: {e}[/red]")
        return 1

    # 3. Valider chaque widget de distribution
    results = []
    for widget_name, target in VALIDATION_TARGETS.items():
        console.print(f"  → Validation de {widget_name}...")

        # Obtenir les données finalisées pour ce widget
        final_data = finalized.get(widget_name)
        if not final_data:
            console.print(
                f"    [yellow]⚠ Widget {widget_name} non trouvé dans les exports[/yellow]"
            )
            continue

        # Exécuter la transformation preview
        try:
            preview_data = execute_transformer(
                sample_data, target["transformer"], target["config"]
            )
        except Exception as e:
            console.print(f"    [red]✗ Erreur transformation: {e}[/red]")
            results.append(
                ValidationResult(
                    widget_name=widget_name,
                    passed=False,
                    max_diff=100.0,
                    errors=[str(e)],
                    preview_proportions=[],
                    finalized_proportions=[],
                    bins_or_categories=[],
                )
            )
            continue

        # Comparer les distributions
        result = compare_distributions(
            preview_data, final_data, widget_name, target["type"]
        )
        results.append(result)

    # 4. Générer le rapport
    generate_report(results, console, len(sample_data))

    # 5. Code de sortie
    all_passed = all(r.passed for r in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
