#!/usr/bin/env python
"""
Convert Shapefiles to GeoPackage format.

Usage:
    python shp_to_gpkg.py <input_path> [--output-dir <output_dir>] [--merge]

Arguments:
    input_path: Path to a shapefile or directory containing shapefiles

Options:
    --output-dir: Output directory for GPKG files (default: same as input)
    --merge: Merge all shapefiles into a single GPKG with multiple layers
    --recursive: Search for shapefiles recursively in subdirectories
"""

import argparse
import logging
from pathlib import Path
import sys
import geopandas as gpd
from typing import List, Optional

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def find_shapefiles(path: Path, recursive: bool = False) -> List[Path]:
    """Find all shapefiles in a directory."""
    shapefiles = []

    if path.is_file() and path.suffix.lower() == ".shp":
        shapefiles.append(path)
    elif path.is_dir():
        pattern = "**/*.shp" if recursive else "*.shp"
        shapefiles = list(path.glob(pattern))

    return shapefiles


def convert_shapefile_to_gpkg(
    shp_path: Path, output_path: Optional[Path] = None, layer_name: Optional[str] = None
) -> Path:
    """Convert a single shapefile to GeoPackage."""
    try:
        logger.info(f"Reading shapefile: {shp_path}")
        gdf = gpd.read_file(shp_path)

        if output_path is None:
            output_path = shp_path.with_suffix(".gpkg")

        if layer_name is None:
            layer_name = shp_path.stem

        logger.info(f"Writing to GeoPackage: {output_path} (layer: {layer_name})")
        gdf.to_file(output_path, driver="GPKG", layer=layer_name)

        logger.info(f"Successfully converted: {shp_path.name} -> {output_path.name}")
        return output_path

    except Exception as e:
        logger.error(f"Failed to convert {shp_path}: {e}")
        raise


def convert_multiple_shapefiles(
    shapefiles: List[Path], output_dir: Optional[Path] = None, merge: bool = False
) -> List[Path]:
    """Convert multiple shapefiles to GeoPackage(s)."""
    converted = []

    if merge and shapefiles:
        # Merge all shapefiles into a single GPKG with multiple layers
        if output_dir is None:
            output_dir = shapefiles[0].parent

        output_path = output_dir / "merged.gpkg"
        logger.info(f"Merging {len(shapefiles)} shapefiles into {output_path}")

        for i, shp_path in enumerate(shapefiles):
            try:
                gdf = gpd.read_file(shp_path)
                layer_name = shp_path.stem

                # For the first layer, create the file; for others, append
                mode = "w" if i == 0 else "a"
                gdf.to_file(output_path, driver="GPKG", layer=layer_name, mode=mode)

                logger.info(f"Added layer '{layer_name}' to {output_path.name}")

            except Exception as e:
                logger.error(f"Failed to add {shp_path} to merged GPKG: {e}")

        converted.append(output_path)
    else:
        # Convert each shapefile to its own GPKG
        for shp_path in shapefiles:
            try:
                if output_dir:
                    output_path = output_dir / f"{shp_path.stem}.gpkg"
                else:
                    output_path = shp_path.with_suffix(".gpkg")

                convert_shapefile_to_gpkg(shp_path, output_path)
                converted.append(output_path)

            except Exception as e:
                logger.error(f"Skipping {shp_path}: {e}")

    return converted


def main():
    parser = argparse.ArgumentParser(
        description="Convert Shapefiles to GeoPackage format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to a shapefile or directory containing shapefiles",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for GPKG files (default: same as input)",
    )

    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge all shapefiles into a single GPKG with multiple layers",
    )

    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search for shapefiles recursively in subdirectories",
    )

    args = parser.parse_args()

    # Validate input path
    if not args.input_path.exists():
        logger.error(f"Input path does not exist: {args.input_path}")
        sys.exit(1)

    # Create output directory if specified
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    # Find shapefiles
    shapefiles = find_shapefiles(args.input_path, args.recursive)

    if not shapefiles:
        logger.warning(f"No shapefiles found in {args.input_path}")
        sys.exit(0)

    logger.info(f"Found {len(shapefiles)} shapefile(s)")

    # Convert shapefiles
    converted = convert_multiple_shapefiles(shapefiles, args.output_dir, args.merge)

    if converted:
        logger.info(
            f"\nConversion complete! Created {len(converted)} GeoPackage file(s):"
        )
        for gpkg in converted:
            logger.info(f"  - {gpkg}")
    else:
        logger.error("No files were successfully converted")
        sys.exit(1)


if __name__ == "__main__":
    main()
