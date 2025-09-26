"""
Bootstrap module for automatic Niamoto instance creation from data files.
This module orchestrates the complete workflow from data discovery to pipeline generation.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
import shutil
from datetime import datetime

from .auto_detector import AutoDetector


class DataBootstrap:
    """Automatic bootstrap from data files to create a working Niamoto instance."""

    def __init__(self, instance_path: Optional[Path] = None):
        """
        Initialize the bootstrap system.

        Args:
            instance_path: Path to the Niamoto instance directory
        """
        self.instance_path = instance_path
        self.detector = AutoDetector()

    def run(
        self,
        data_dir: Path,
        output_dir: Optional[Path] = None,
        auto_confirm: bool = False,
        interactive: bool = True,
    ) -> Dict[str, Any]:
        """
        Run complete bootstrap process.

        Args:
            data_dir: Directory containing data files
            output_dir: Directory to write configuration files (default: data_dir/../config)
            auto_confirm: Skip confirmation prompts
            interactive: Show interactive progress

        Returns:
            Dictionary with bootstrap results
        """
        results = {
            "status": "started",
            "timestamp": datetime.now().isoformat(),
            "data_dir": str(data_dir),
            "steps": [],
        }

        # Step 1: Analyze data
        if interactive:
            print("🔍 Step 1: Analyzing data files...")

        analysis = self.detector.analyze_directory(data_dir)
        results["analysis"] = analysis
        results["steps"].append(
            {
                "name": "analysis",
                "status": "completed",
                "files_analyzed": len(analysis["profiles"]),
                "confidence": analysis["confidence"],
            }
        )

        if interactive:
            self._display_analysis_summary(analysis)

        # Step 2: Validate and confirm
        if not auto_confirm and interactive:
            if not self._confirm_configuration(analysis):
                results["status"] = "cancelled"
                return results

        # Step 3: Generate configurations
        if interactive:
            print("\n⚙️  Step 2: Generating configuration files...")

        configs = self._generate_all_configs(analysis["config"])
        results["configs"] = configs
        results["steps"].append(
            {
                "name": "config_generation",
                "status": "completed",
                "configs_created": list(configs.keys()),
            }
        )

        # Step 4: Save configurations
        if output_dir is None:
            output_dir = data_dir.parent / "config"

        if interactive:
            print(f"\n💾 Step 3: Saving configurations to {output_dir}...")

        saved_files = self._save_configurations(configs, output_dir)
        results["saved_files"] = saved_files
        results["steps"].append(
            {"name": "save_configs", "status": "completed", "files": saved_files}
        )

        # Step 5: Create instance structure
        if self.instance_path:
            if interactive:
                print(
                    f"\n🏗️  Step 4: Creating instance structure at {self.instance_path}..."
                )

            self._create_instance_structure(self.instance_path, data_dir, output_dir)
            results["instance_created"] = True
            results["steps"].append(
                {
                    "name": "create_instance",
                    "status": "completed",
                    "path": str(self.instance_path),
                }
            )

        results["status"] = "completed"

        if interactive:
            self._display_completion_message(results)

        return results

    def _display_analysis_summary(self, analysis: Dict[str, Any]) -> None:
        """Display analysis summary to user."""
        summary = analysis["summary"]

        print("\n✅ Analysis complete!")
        print(
            f"   Found {summary['total_files']} files with {summary['total_records']:,} total records"
        )
        print(f"   Confidence: {analysis['confidence'] * 100:.0f}%")

        if analysis["validation"]["warnings"]:
            print("\n⚠️  Warnings:")
            for warning in analysis["validation"]["warnings"]:
                print(f"   - {warning}")

    def _confirm_configuration(self, analysis: Dict[str, Any]) -> bool:
        """Ask user to confirm the detected configuration."""
        print("\n" + "=" * 60)
        print("DETECTED CONFIGURATION")
        print("=" * 60)

        # Show detected entities
        for entity_type, entities in analysis["summary"]["detected_entities"].items():
            print(f"\n{entity_type.upper()}:")
            for entity in entities:
                print(f"  • {entity['name']} ({entity['records']:,} records)")

        print("\n" + "=" * 60)
        response = input("Proceed with this configuration? [Y/n]: ")
        return response.lower() in ["", "y", "yes"]

    def _generate_all_configs(self, import_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate all necessary configuration files."""
        configs = {}

        # 1. Import configuration (already generated)
        configs["import.yml"] = import_config

        # 2. Transform configuration
        configs["transform.yml"] = self._generate_transform_config(import_config)

        # 3. Export configuration
        configs["export.yml"] = self._generate_export_config(import_config)

        return configs

    def _generate_transform_config(
        self, import_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate transform configuration based on import config."""
        transforms = []

        # Create transform for each reference entity
        for ref_name, ref_config in import_config.get("references", {}).items():
            # Find matching data sources
            data_sources = []
            for data_name, data_config in import_config.get("data", {}).items():
                # Check if data links to this reference
                for link in data_config.get("links", []):
                    if link.get("reference") == ref_name:
                        data_sources.append(data_name)
                        break

            # If no explicit links, use the main data source
            if not data_sources and import_config.get("data"):
                data_sources = [list(import_config["data"].keys())[0]]

            if data_sources:
                transform = {
                    "group_by": ref_name,
                    "sources": [
                        {
                            "name": data_sources[0],
                            "data": data_sources[0],
                            "grouping": ref_name,
                        }
                    ],
                    "widgets_data": {
                        "statistics": {
                            "plugin": "statistical_summary",
                            "params": {"calculations": ["count", "mean", "std"]},
                        },
                        "distribution": {
                            "plugin": "categorical_distribution",
                            "params": {"top_n": 10},
                        },
                    },
                }
                transforms.append(transform)

        # Add a default transform if we have data but no references
        if not transforms and import_config.get("data"):
            data_name = list(import_config["data"].keys())[0]
            transforms.append(
                {
                    "group_by": "all",
                    "sources": [{"name": data_name, "data": data_name}],
                    "widgets_data": {
                        "summary": {
                            "plugin": "statistical_summary",
                            "params": {"calculations": ["count"]},
                        }
                    },
                }
            )

        return transforms

    def _generate_export_config(self, import_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate export configuration based on import config."""
        config = {
            "site": {
                "title": "Niamoto Data Explorer",
                "description": "Automatically generated Niamoto instance",
                "url": "http://localhost:8000",
                "theme": "default",
            },
            "pages": [],
        }

        # Create a page for each reference entity
        for ref_name in import_config.get("references", {}):
            config["pages"].append(
                {
                    "id": ref_name,
                    "title": ref_name.replace("_", " ").title(),
                    "template": "dashboard",
                    "data_source": ref_name,
                    "widgets": [
                        {"type": "statistics", "position": "top"},
                        {"type": "distribution", "position": "main"},
                        {"type": "map", "position": "side"},
                    ],
                }
            )

        # Add home page
        config["pages"].insert(
            0,
            {
                "id": "home",
                "title": "Home",
                "template": "home",
                "content": "Welcome to your Niamoto instance",
            },
        )

        return config

    def _save_configurations(
        self, configs: Dict[str, Any], output_dir: Path
    ) -> List[str]:
        """Save configuration files to directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_files = []

        for filename, content in configs.items():
            file_path = output_dir / filename

            # Backup existing file if it exists
            if file_path.exists():
                backup_path = file_path.with_suffix(
                    f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                shutil.copy(file_path, backup_path)
                print(f"   Backed up existing {filename} to {backup_path.name}")

            with open(file_path, "w") as f:
                yaml.dump(content, f, default_flow_style=False, sort_keys=False)

            saved_files.append(str(file_path))
            print(f"   ✓ Saved {filename}")

        return saved_files

    def _create_instance_structure(
        self, instance_path: Path, data_dir: Path, config_dir: Path
    ) -> None:
        """Create complete instance directory structure."""
        # Create directories
        (instance_path / "config").mkdir(parents=True, exist_ok=True)
        (instance_path / "data").mkdir(parents=True, exist_ok=True)
        (instance_path / "exports").mkdir(parents=True, exist_ok=True)
        (instance_path / "logs").mkdir(parents=True, exist_ok=True)

        # Copy or link configurations
        if config_dir != instance_path / "config":
            for config_file in config_dir.glob("*.yml"):
                shutil.copy(config_file, instance_path / "config" / config_file.name)

        # Create README
        readme_content = f"""# Niamoto Instance

Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Data source: {data_dir}

## Quick Start

1. Import data:
   ```bash
   niamoto import --config config/import.yml
   ```

2. Run transformations:
   ```bash
   niamoto transform --config config/transform.yml
   ```

3. Export site:
   ```bash
   niamoto export --config config/export.yml
   ```

## Configuration Files

- `config/import.yml`: Data import configuration
- `config/transform.yml`: Data transformation pipelines
- `config/export.yml`: Site export settings

## Data

Original data files are in: {data_dir}
"""
        with open(instance_path / "README.md", "w") as f:
            f.write(readme_content)

        print("   ✓ Created instance structure")
        print("   ✓ Created README.md")

    def _display_completion_message(self, results: Dict[str, Any]) -> None:
        """Display completion message with next steps."""
        print("\n" + "🎉 " * 20)
        print("BOOTSTRAP COMPLETE!")
        print("🎉 " * 20)

        print("\n📁 Configuration files saved:")
        for file_path in results.get("saved_files", []):
            print(f"   • {file_path}")

        if results.get("instance_created"):
            print(f"\n🏗️  Instance created at: {results['steps'][-1]['path']}")

        print("\n🚀 Next steps:")
        print("   1. Review and adjust the generated configurations if needed")
        print("   2. Run: niamoto import")
        print("   3. Run: niamoto transform")
        print("   4. Run: niamoto export")
        print("   5. View your site at: http://localhost:8000")

        print("\n💡 Tip: Use 'niamoto gui' to manage your instance visually")


def bootstrap_from_directory(
    data_dir: Path,
    output_dir: Optional[Path] = None,
    instance_path: Optional[Path] = None,
    auto_confirm: bool = False,
) -> Dict[str, Any]:
    """
    Convenience function to bootstrap from a directory.

    Args:
        data_dir: Directory containing data files
        output_dir: Where to save configurations
        instance_path: Optional path to create full instance
        auto_confirm: Skip confirmation prompts

    Returns:
        Bootstrap results
    """
    bootstrap = DataBootstrap(instance_path)
    return bootstrap.run(data_dir, output_dir, auto_confirm=auto_confirm)
