#!/usr/bin/env python3
"""Crée une instance niamoto-subset à partir de niamoto-nc pour des tests rapides.

Extrait un sous-ensemble cohérent :
- 4 familles (~250 occurrences max chacune → ~1000 total vs 203k)
- Tous les plots (22 lignes)
- 2 shapes légers (holdridge_zones + mines)
- Stats pré-calculées filtrées
- Rasters légers en symlink
- Configs adaptées (transform.yml + export.yml copiées telles quelles)
"""

import shutil
import sys
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TARGET_FAMILIES = 4
MAX_OCCURRENCES_PER_FAMILY = 250

# Shapes à inclure (nom dans import.yml → fichier source)
SHAPES_TO_KEEP = {
    "Zones de vie": {
        "path": "imports/shapes/holdridge_zones.gpkg",
        "name_field": "zone",
    },
    "Emprises minieres": {
        "path": "imports/shapes/mines.gpkg",
        "name_field": "region",
    },
}

# Préfixes des shape IDs dans raw_shape_stats.csv
SHAPE_STATS_PREFIXES = ("zone_de_vie_", "emprises_minieres_")

# Rasters légers à inclure (symlinks)
RASTERS_TO_KEEP = [
    "rainfall_epsg3163.tif",
    "amap_raster_holdridge_nc.tif",
]

# Layers metadata à garder dans import.yml
LAYERS_TO_KEEP = ["rainfall", "holdridge"]


# ---------------------------------------------------------------------------
# Extraction des occurrences
# ---------------------------------------------------------------------------


def extract_occurrences(
    source: Path,
    dest: Path,
    target_families: int = TARGET_FAMILIES,
    max_per_family: int = MAX_OCCURRENCES_PER_FAMILY,
) -> pd.DataFrame:
    """Extrait un subset d'occurrences par familles."""
    print(f"  Lecture de {source.name}...")
    df = pd.read_csv(source)
    print(f"  {len(df):,} lignes originales")

    family_counts = df["family"].value_counts()
    # Familles entre 50 et 2000 occurrences
    valid = family_counts[(family_counts > 50) & (family_counts < 2000)]
    selected = valid.head(target_families).index.tolist()

    print("  Familles sélectionnées :")
    for fam in selected:
        print(f"    - {fam} ({family_counts[fam]:,} occ)")

    parts = []
    for fam in selected:
        fam_data = df[df["family"] == fam]
        if len(fam_data) > max_per_family:
            fam_data = fam_data.sample(n=max_per_family, random_state=42)
        parts.append(fam_data)

    subset = pd.concat(parts, ignore_index=True)
    subset.to_csv(dest, index=False)

    print(
        f"  -> {len(subset):,} lignes, {subset['family'].nunique()} familles, "
        f"{subset['genus'].nunique()} genres, {subset['species'].nunique()} espèces"
    )
    return subset


# ---------------------------------------------------------------------------
# Filtrage des stats shapes
# ---------------------------------------------------------------------------


def filter_shape_stats(source: Path, dest: Path) -> None:
    """Filtre raw_shape_stats.csv pour ne garder que les shapes inclus."""
    df = pd.read_csv(source, sep=";")
    mask = df["id"].str.startswith(SHAPE_STATS_PREFIXES)
    filtered = df[mask]
    filtered.to_csv(dest, sep=";", index=False)
    print(f"  raw_shape_stats.csv : {len(df):,} -> {len(filtered):,} lignes")


# ---------------------------------------------------------------------------
# Création de la structure de l'instance
# ---------------------------------------------------------------------------


def create_instance(source_dir: Path, target_dir: Path) -> None:
    """Crée l'instance niamoto-subset complète."""

    if target_dir.exists():
        shutil.rmtree(target_dir)

    # Répertoires
    for subdir in [
        "config",
        "imports/shapes",
        "imports/layers",
        "db",
        "exports/web",
        "exports/api",
        "logs",
        "plugins",
    ]:
        (target_dir / subdir).mkdir(parents=True, exist_ok=True)

    # --- Données ---

    print("\n[1/5] Occurrences")
    extract_occurrences(
        source_dir / "imports" / "occurrences.csv",
        target_dir / "imports" / "occurrences.csv",
    )

    print("\n[2/5] Plots")
    shutil.copy2(
        source_dir / "imports" / "plots.csv",
        target_dir / "imports" / "plots.csv",
    )
    shutil.copy2(
        source_dir / "imports" / "raw_plot_stats.csv",
        target_dir / "imports" / "raw_plot_stats.csv",
    )
    print("  plots.csv + raw_plot_stats.csv copiés")

    print("\n[3/5] Shapes (symlinks)")
    for shape_info in SHAPES_TO_KEEP.values():
        # Les gpkg sont à imports/ root dans niamoto-nc
        # mais l'import.yml les référence dans imports/shapes/
        gpkg_name = Path(shape_info["path"]).name
        shape_file = source_dir / "imports" / gpkg_name
        if shape_file.exists():
            link = target_dir / shape_info["path"]
            link.symlink_to(shape_file.resolve())
            print(f"  -> {shape_info['path']} (source: imports/{gpkg_name})")
        else:
            print(f"  ATTENTION: {shape_file} introuvable")

    print("\n[4/5] Stats shapes filtrées")
    filter_shape_stats(
        source_dir / "imports" / "raw_shape_stats.csv",
        target_dir / "imports" / "raw_shape_stats.csv",
    )

    print("\n[5/5] Rasters (symlinks)")
    for raster in RASTERS_TO_KEEP:
        src = source_dir / "imports" / raster
        if src.exists():
            link = target_dir / "imports" / "layers" / raster
            link.symlink_to(src.resolve())
            print(f"  -> layers/{raster}")
        else:
            print(f"  ATTENTION: {src} introuvable")

    # --- Templates (symlink vers niamoto-nc) ---
    templates_src = source_dir / "templates"
    if templates_src.exists():
        (target_dir / "templates").symlink_to(templates_src.resolve())
        print("\n  templates/ -> symlink vers niamoto-nc")

    # --- Configs ---
    print("\n[Configs]")
    write_config_yml(target_dir / "config" / "config.yml")
    write_import_yml(target_dir / "config" / "import.yml")

    # transform.yml et export.yml : copie directe
    for cfg in ["transform.yml", "export.yml"]:
        shutil.copy2(source_dir / "config" / cfg, target_dir / "config" / cfg)
        print(f"  {cfg} copié")

    # --- Résumé ---
    print_summary(source_dir, target_dir)


# ---------------------------------------------------------------------------
# Génération des configs
# ---------------------------------------------------------------------------


def write_config_yml(dest: Path) -> None:
    """Écrit config.yml pour l'instance subset."""
    dest.write_text("""\
project:
  name: niamoto-subset
  version: 1.0.0
  niamoto_version: 0.8.0
database:
  path: db/niamoto.duckdb
logs:
  path: logs
exports:
  web: exports/web
  api: exports/api
plugins:
  path: plugins
templates:
  path: templates
""")
    print("  config.yml généré")


def write_import_yml(dest: Path) -> None:
    """Écrit import.yml adapté (2 shapes, rasters légers)."""
    # Construire la section sources des shapes
    shape_sources = ""
    for name, info in SHAPES_TO_KEEP.items():
        shape_sources += f"""          - name: {name}
            path: {info["path"]}
            name_field: {info["name_field"]}
"""

    # Construire la section layers
    layers_section = ""
    layers_data = {
        "rainfall": {
            "type": "raster",
            "path": "imports/layers/rainfall_epsg3163.tif",
            "description": "Annual rainfall distribution",
        },
        "holdridge": {
            "type": "raster",
            "path": "imports/layers/amap_raster_holdridge_nc.tif",
            "description": "Holdridge life zones",
        },
    }
    for name in LAYERS_TO_KEEP:
        layer = layers_data[name]
        layers_section += f"""  - name: {name}
    type: {layer["type"]}
    path: {layer["path"]}
    description: {layer["description"]}
"""

    content = f"""\
version: '1.0'
entities:
  datasets:
    occurrences:
      connector:
        type: file
        format: csv
        path: imports/occurrences.csv
  references:
    taxons:
      kind: hierarchical
      description: Taxonomic reference extracted from the occurrences dataset.
      connector:
        type: derived
        source: occurrences
        extraction:
          levels:
          - name: family
            column: family
          - name: genus
            column: genus
          - name: species
            column: species
          - name: infra
            column: infra
          id_column: id_taxonref
          name_column: taxaname
          incomplete_rows: skip
          id_strategy: hash
      hierarchy:
        strategy: adjacency_list
        levels:
        - family
        - genus
        - species
        - infra
      schema:
        fields: []
    plots:
      description: Plot and site reference catalogue used for spatial aggregation.
      connector:
        type: file
        format: csv
        path: imports/plots.csv
      schema:
        id_field: id_plot
        fields:
        - name: plot
          type: string
          description: Plot label used in reports.
        - name: geo_pt
          type: geometry
        - name: locality
          type: string
        - name: plot_name
          type: string
      relation:
        dataset: occurrences
        foreign_key: plot_name
        reference_key: plot
      links:
      - entity: occurrences
        field: locality
        target_field: plot_name
    shapes:
      kind: spatial
      description: Geographic reference features for spatial analysis (subset).
      connector:
        type: file_multi_feature
        sources:
{shape_sources.rstrip()}
      schema:
        id_field: id
        fields:
          - name: name
            type: string
            description: Feature name from source file
          - name: location
            type: geometry
            description: Geometry in WKT format
          - name: entity_type
            type: string
            description: Source type
metadata:
  layers:
{layers_section.rstrip()}
"""
    dest.write_text(content)
    print("  import.yml généré (2 shapes, 2 rasters)")


# ---------------------------------------------------------------------------
# Résumé
# ---------------------------------------------------------------------------


def print_summary(source_dir: Path, target_dir: Path) -> None:
    """Affiche un résumé de la taille de l'instance."""

    def dir_size(path: Path) -> int:
        total = 0
        for f in path.rglob("*"):
            if f.is_file() and not f.is_symlink():
                total += f.stat().st_size
        return total

    def symlink_size(path: Path) -> int:
        total = 0
        for f in path.rglob("*"):
            if f.is_symlink():
                target = f.resolve()
                if target.exists():
                    total += target.stat().st_size
        return total

    own = dir_size(target_dir)
    linked = symlink_size(target_dir)
    source_total = dir_size(source_dir) + symlink_size(source_dir)

    print("\n" + "=" * 60)
    print("  Instance niamoto-subset créée")
    print("=" * 60)
    print(f"  Fichiers propres : {own / 1024:.0f} Ko")
    print(f"  Symlinks (taille réelle) : {linked / (1024 * 1024):.1f} Mo")
    print(f"  Source niamoto-nc : {source_total / (1024 * 1024):.0f} Mo")
    print("\n  Prochaines étapes :")
    print(f"    cd {target_dir}")
    print("    niamoto import")
    print("    niamoto transform")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    project_root = Path(__file__).parent.parent.parent
    source_dir = project_root / "test-instance" / "niamoto-nc"
    target_dir = project_root / "test-instance" / "niamoto-subset"

    if not (source_dir / "imports" / "occurrences.csv").exists():
        print(f"Erreur : {source_dir / 'imports' / 'occurrences.csv'} introuvable")
        sys.exit(1)

    print("=" * 60)
    print("  Création de l'instance niamoto-subset")
    print("=" * 60)

    create_instance(source_dir, target_dir)


if __name__ == "__main__":
    main()
