"""
Auto-detector for analyzing data files and generating import configurations.
This module orchestrates the profiling and generates suggested configurations.
"""

from pathlib import Path
from typing import List, Dict, Any
import yaml
from .profiler import DataProfiler, DatasetProfile


class AutoDetector:
    """Automatically detects data structure and suggests configuration."""

    def __init__(self):
        """Initialize the auto-detector."""
        self.profiler = DataProfiler()

    def analyze_directory(self, directory: Path) -> Dict[str, Any]:
        """
        Analyze all files in a directory and suggest configuration.

        Args:
            directory: Path to directory containing data files

        Returns:
            Dictionary containing analysis results and suggested configuration
        """
        files = self._discover_files(directory)
        profiles = []

        for file_path in files:
            try:
                profile = self.profiler.profile(file_path)
                profiles.append(profile)
                print(
                    f"✓ Analyzed {file_path.name}: {profile.detected_type} ({profile.record_count} records)"
                )
            except Exception as e:
                print(f"✗ Failed to analyze {file_path.name}: {e}")

        # Generate configuration from profiles
        config = self._generate_config(profiles)

        # Validate configuration
        validation = self._validate_config(config, profiles)

        # Calculate overall confidence
        confidence = self._calculate_overall_confidence(profiles)

        return {
            "config": config,
            "profiles": [p.to_dict() for p in profiles],
            "validation": validation,
            "confidence": confidence,
            "summary": self._generate_summary(profiles),
        }

    def analyze_files(self, file_paths: List[Path]) -> Dict[str, Any]:
        """
        Analyze specific files and suggest configuration.

        Args:
            file_paths: List of file paths to analyze

        Returns:
            Dictionary containing analysis results
        """
        profiles = []

        for file_path in file_paths:
            try:
                profile = self.profiler.profile(file_path)
                profiles.append(profile)
            except Exception as e:
                print(f"Failed to analyze {file_path}: {e}")

        config = self._generate_config(profiles)
        validation = self._validate_config(config, profiles)

        return {
            "config": config,
            "profiles": [p.to_dict() for p in profiles],
            "validation": validation,
            "confidence": self._calculate_overall_confidence(profiles),
        }

    def _discover_files(self, directory: Path) -> List[Path]:
        """Discover relevant data files in a directory."""
        supported_extensions = {
            ".csv",
            ".geojson",
            ".json",
            ".shp",
            ".gpkg",
            ".xlsx",
            ".xls",
        }
        files = []

        # Direct files in the directory
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                # Skip temporary or hidden files
                if not file_path.name.startswith(".") and not file_path.name.startswith(
                    "~"
                ):
                    files.append(file_path)

        # Look in subdirectories for shapes
        shapes_dir = directory / "shapes"
        if shapes_dir.exists():
            for shape_path in shapes_dir.iterdir():
                if (
                    shape_path.is_file()
                    and shape_path.suffix.lower() in supported_extensions
                ):
                    files.append(shape_path)
                elif shape_path.is_dir():
                    # Look for shapefiles in subdirectories
                    for subfile in shape_path.glob("*.shp"):
                        files.append(subfile)
                        break  # Only need one .shp per directory

        return sorted(files)

    def _generate_config(self, profiles: List[DatasetProfile]) -> Dict[str, Any]:
        """Generate import configuration from profiles."""
        config = {"references": {}, "data": {}, "shapes": [], "layers": []}

        # Check if we need to extract taxonomy from occurrences
        taxonomy_extracted = False
        for profile in profiles:
            if (
                "occurrence" in profile.suggested_name
                or "observation" in profile.suggested_name
            ):
                # Check if it contains taxonomy columns
                has_taxonomy = any(
                    col.semantic_type and "taxonomy" in col.semantic_type
                    for col in profile.columns
                )
                if has_taxonomy:
                    # Create extracted taxonomy reference
                    config["references"]["taxonomy"] = {
                        "source": str(
                            profile.file_path.relative_to(
                                profile.file_path.parent.parent
                            )
                        ),
                        "type": "hierarchical",
                        "extract_from": "occurrences",
                        "hierarchy": [
                            col.name
                            for col in profile.columns
                            if col.semantic_type
                            and "taxonomy" in col.semantic_type
                            and col.semantic_type.split(".")[-1]
                            in ["family", "genus", "species"]
                        ],
                        "id_field": next(
                            (
                                col.name
                                for col in profile.columns
                                if col.semantic_type == "reference.taxon"
                            ),
                            "id_taxonref",
                        ),
                    }
                    taxonomy_extracted = True
                    break  # Avoid extracting taxonomy multiple times

        # Process each profile
        for profile in profiles:
            # Determine category based on type and name
            if self._is_reference_entity(profile):
                # Skip if this is a taxonomy file and we already extracted from occurrences
                if taxonomy_extracted and profile.detected_type == "hierarchical":
                    continue
                config["references"][profile.suggested_name] = (
                    self._create_reference_config(profile)
                )
            elif self._is_shape_entity(profile):
                config["shapes"].append(self._create_shape_config(profile))
            elif self._is_layer_entity(profile):
                config["layers"].append(self._create_layer_config(profile))
            else:
                # Factual data (occurrences, observations)
                config["data"][profile.suggested_name] = self._create_data_config(
                    profile, profiles
                )

        # Clean up empty sections
        if not config["shapes"]:
            del config["shapes"]
        if not config["layers"]:
            del config["layers"]

        return config

    def _is_reference_entity(self, profile: DatasetProfile) -> bool:
        """Check if profile represents a reference entity."""
        # Taxonomic hierarchies are references
        if profile.detected_type == "hierarchical":
            return True

        # Small datasets with unique identifiers are likely references
        if profile.record_count < 1000:
            # Check for ID columns
            for col in profile.columns:
                col_lower = col.name.lower()
                # Look for ID patterns
                if (
                    "id_" in col_lower
                    or col_lower.startswith("id")
                    or col_lower.endswith("_id")
                    or col_lower == "id"
                ):
                    # High unique ratio suggests reference table
                    if col.unique_ratio > 0.5:
                        return True

        # Plot/location files are references
        if "plot" in profile.suggested_name or "location" in profile.suggested_name:
            # Small plot files are references
            if profile.record_count < 10000:
                return True

        return False

    def _is_shape_entity(self, profile: DatasetProfile) -> bool:
        """Check if profile represents a shape entity."""
        return profile.detected_type == "spatial" and (
            "shape" in str(profile.file_path).lower()
            or profile.file_path.parent.name == "shapes"
        )

    def _is_layer_entity(self, profile: DatasetProfile) -> bool:
        """Check if profile represents a layer."""
        return (
            "layer" in str(profile.file_path).lower()
            or profile.file_path.parent.name == "layers"
        )

    def _create_reference_config(self, profile: DatasetProfile) -> Dict[str, Any]:
        """Create configuration for a reference entity."""
        config = {
            "source": str(
                profile.file_path.relative_to(profile.file_path.parent.parent)
            ),
            "type": profile.detected_type,
        }

        # Add hierarchy information for taxonomic data
        if profile.detected_type == "hierarchical":
            hierarchy_cols = []
            for col in profile.columns:
                if col.semantic_type and "taxonomy" in col.semantic_type:
                    level = col.semantic_type.split(".")[-1]
                    if level in ["family", "genus", "species", "infra"]:
                        hierarchy_cols.append(col.name)

            if hierarchy_cols:
                config["hierarchy"] = hierarchy_cols

            # Find ID column
            for col in profile.columns:
                if col.semantic_type == "taxonomy.taxon_id":
                    config["id_field"] = col.name
                    break

        # Add spatial information
        elif profile.detected_type == "spatial":
            for col in profile.columns:
                col_lower = col.name.lower()
                if col.semantic_type == "identifier" or "id_" in col_lower:
                    config["id_field"] = col.name
                    break

            for col in profile.columns:
                col_lower = col.name.lower()
                if col.semantic_type == "location.plot" or col_lower == "plot":
                    config["name_field"] = col.name
                elif col.semantic_type == "geometry" or col_lower == "geo_pt":
                    config["geometry_field"] = col.name

        return config

    def _create_shape_config(self, profile: DatasetProfile) -> Dict[str, Any]:
        """Create configuration for a shape entity."""
        config = {
            "type": profile.suggested_name.replace("_", " ").title(),
            "path": str(profile.file_path.relative_to(profile.file_path.parent.parent)),
        }

        # Find name field
        for col in profile.columns:
            col_lower = col.name.lower()
            if any(term in col_lower for term in ["name", "nom", "label", "libelle"]):
                config["name_field"] = col.name
                break

        return config

    def _create_layer_config(self, profile: DatasetProfile) -> Dict[str, Any]:
        """Create configuration for a layer."""
        return {
            "name": profile.suggested_name,
            "type": "raster"
            if profile.file_path.suffix in [".tif", ".tiff"]
            else "vector",
            "path": str(profile.file_path.relative_to(profile.file_path.parent.parent)),
            "description": f"{profile.suggested_name} layer",
        }

    def _create_data_config(
        self, profile: DatasetProfile, all_profiles: List[DatasetProfile]
    ) -> Dict[str, Any]:
        """Create configuration for factual data."""
        config = {
            "source": str(
                profile.file_path.relative_to(profile.file_path.parent.parent)
            )
        }

        # Detect links to reference entities
        links = []

        # Get all reference profiles
        reference_profiles = [p for p in all_profiles if self._is_reference_entity(p)]

        # Check columns for references
        for col in profile.columns:
            if col.semantic_type and col.semantic_type.startswith("reference."):
                ref_type = col.semantic_type.split(".")[-1]

                # Map to actual reference names
                if ref_type == "taxon":
                    # Look for taxonomic reference (might not exist if embedded in occurrences)
                    for ref_profile in reference_profiles:
                        if ref_profile.detected_type == "hierarchical":
                            if not any(link["field"] == col.name for link in links):
                                links.append(
                                    {
                                        "reference": ref_profile.suggested_name,
                                        "field": col.name,
                                    }
                                )
                            break

                elif ref_type == "plot":
                    # Find plot/location reference
                    for ref_profile in reference_profiles:
                        if (
                            "plot" in ref_profile.suggested_name
                            or "location" in ref_profile.suggested_name
                        ):
                            if not any(link["field"] == col.name for link in links):
                                links.append(
                                    {
                                        "reference": ref_profile.suggested_name,
                                        "field": col.name,
                                    }
                                )
                            break

        if links:
            config["links"] = links

        # Add geometry field if present
        for col in profile.columns:
            if col.semantic_type == "geometry":
                config["geometry_field"] = col.name
                break

        return config

    def _validate_config(
        self, config: Dict[str, Any], profiles: List[DatasetProfile]
    ) -> Dict[str, Any]:
        """Validate the generated configuration."""
        issues = []
        warnings = []

        # Check for at least one reference or data entity
        if not config.get("references") and not config.get("data"):
            issues.append("No reference entities or data detected")

        # Check for orphan data (data without links)
        for data_name, data_config in config.get("data", {}).items():
            if not data_config.get("links"):
                warnings.append(
                    f"Data '{data_name}' has no detected links to references"
                )

        # Check for duplicate entity names
        all_names = list(config.get("references", {}).keys()) + list(
            config.get("data", {}).keys()
        )
        if len(all_names) != len(set(all_names)):
            issues.append("Duplicate entity names detected")

        return {"valid": len(issues) == 0, "issues": issues, "warnings": warnings}

    def _calculate_overall_confidence(self, profiles: List[DatasetProfile]) -> float:
        """Calculate overall confidence score."""
        if not profiles:
            return 0.0

        total_confidence = sum(p.confidence for p in profiles)
        avg_confidence = total_confidence / len(profiles)

        # Boost if we have coherent set (references + data)
        has_references = any(self._is_reference_entity(p) for p in profiles)
        has_data = any(
            not self._is_reference_entity(p) and not self._is_shape_entity(p)
            for p in profiles
        )

        if has_references and has_data:
            avg_confidence = min(1.0, avg_confidence * 1.1)

        return round(avg_confidence, 2)

    def _generate_summary(self, profiles: List[DatasetProfile]) -> Dict[str, Any]:
        """Generate human-readable summary of detection."""
        summary = {
            "total_files": len(profiles),
            "total_records": sum(p.record_count for p in profiles),
            "detected_entities": {},
        }

        for profile in profiles:
            entity_type = "references" if self._is_reference_entity(profile) else "data"
            if self._is_shape_entity(profile):
                entity_type = "shapes"

            if entity_type not in summary["detected_entities"]:
                summary["detected_entities"][entity_type] = []

            summary["detected_entities"][entity_type].append(
                {
                    "name": profile.suggested_name,
                    "type": profile.detected_type,
                    "records": profile.record_count,
                    "file": profile.file_path.name,
                }
            )

        return summary

    def save_config(self, config: Dict[str, Any], output_path: Path) -> None:
        """Save configuration to YAML file."""
        with open(output_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
