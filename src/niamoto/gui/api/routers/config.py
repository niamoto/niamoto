"""Configuration API endpoints."""

import os
from typing import Dict, Any, Optional
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter()


class ProjectInfo(BaseModel):
    """Project information model."""

    name: str
    version: Optional[str] = "1.0.0"
    niamoto_version: Optional[str] = None
    created_at: Optional[str] = None


class ImportConfig(BaseModel):
    """Import configuration model."""

    taxonomy_csv: str = Field(..., description="Path to taxonomy CSV file")
    occurrences_csv: str = Field(..., description="Path to occurrences CSV file")
    plots_csv: str | None = Field(None, description="Path to plots CSV file")


class TransformConfig(BaseModel):
    """Transform configuration model."""

    plugins: list[Dict[str, Any]] = Field(
        default_factory=list, description="List of transform plugins"
    )


class ExportConfig(BaseModel):
    """Export configuration model."""

    output_dir: str = Field(..., description="Output directory for generated files")
    plugins: list[Dict[str, Any]] = Field(
        default_factory=list, description="List of export plugins"
    )


class PipelineConfig(BaseModel):
    """Complete pipeline configuration."""

    import_config: ImportConfig
    transform_config: TransformConfig
    export_config: ExportConfig


@router.post("/validate")
async def validate_config(config: PipelineConfig) -> Dict[str, Any]:
    """Validate a pipeline configuration."""
    try:
        # Basic validation is done by Pydantic
        # Add custom validation logic here
        return {"valid": True, "message": "Configuration is valid"}
    except Exception as e:
        return {"valid": False, "message": str(e)}


@router.post("/generate-yaml")
async def generate_yaml(config: PipelineConfig) -> Dict[str, str]:
    """Generate YAML files from configuration."""
    try:
        # Generate import.yml
        import_yaml = yaml.dump(
            {
                "sources": [
                    {
                        "name": "taxonomy",
                        "type": "csv",
                        "path": config.import_config.taxonomy_csv,
                    },
                    {
                        "name": "occurrences",
                        "type": "csv",
                        "path": config.import_config.occurrences_csv,
                    },
                ]
            },
            default_flow_style=False,
        )

        # Add plots if provided
        if config.import_config.plots_csv:
            import_data = yaml.safe_load(import_yaml)
            import_data["sources"].append(
                {"name": "plots", "type": "csv", "path": config.import_config.plots_csv}
            )
            import_yaml = yaml.dump(import_data, default_flow_style=False)

        # Generate transform.yml
        transform_yaml = yaml.dump(
            {"transforms": config.transform_config.plugins}, default_flow_style=False
        )

        # Generate export.yml
        export_yaml = yaml.dump(
            {
                "output_dir": config.export_config.output_dir,
                "exports": config.export_config.plugins,
            },
            default_flow_style=False,
        )

        return {
            "import.yml": import_yaml,
            "transform.yml": transform_yaml,
            "export.yml": export_yaml,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def get_templates() -> Dict[str, Any]:
    """Get available configuration templates."""
    return {
        "templates": [
            {
                "id": "basic",
                "name": "Basic Configuration",
                "description": "Simple configuration with taxonomy and occurrences",
            },
            {
                "id": "full",
                "name": "Full Configuration",
                "description": "Complete configuration with plots and all plugins",
            },
        ]
    }


@router.get("/templates/{template_id}")
async def get_template(template_id: str) -> PipelineConfig:
    """Get a specific configuration template."""
    templates = {
        "basic": PipelineConfig(
            import_config=ImportConfig(
                taxonomy_csv="data/taxonomy.csv", occurrences_csv="data/occurrences.csv"
            ),
            transform_config=TransformConfig(
                plugins=[
                    {
                        "name": "top_species",
                        "type": "statistics",
                        "config": {"limit": 10},
                    }
                ]
            ),
            export_config=ExportConfig(
                output_dir="output",
                plugins=[
                    {
                        "name": "static_site",
                        "type": "website",
                        "config": {"theme": "default"},
                    }
                ],
            ),
        ),
        "full": PipelineConfig(
            import_config=ImportConfig(
                taxonomy_csv="data/taxonomy.csv",
                occurrences_csv="data/occurrences.csv",
                plots_csv="data/plots.csv",
            ),
            transform_config=TransformConfig(
                plugins=[
                    {
                        "name": "top_species",
                        "type": "statistics",
                        "config": {"limit": 10},
                    },
                    {
                        "name": "distribution_maps",
                        "type": "spatial",
                        "config": {"resolution": "high"},
                    },
                ]
            ),
            export_config=ExportConfig(
                output_dir="output",
                plugins=[
                    {
                        "name": "static_site",
                        "type": "website",
                        "config": {"theme": "modern"},
                    },
                    {
                        "name": "data_export",
                        "type": "data",
                        "config": {"format": "geojson"},
                    },
                ],
            ),
        ),
    }

    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")

    return templates[template_id]


@router.get("/project")
async def get_project_info() -> ProjectInfo:
    """Get project information from config.yml."""
    try:
        # Get config directory
        niamoto_home = os.environ.get("NIAMOTO_HOME", os.getcwd())
        config_path = os.path.join(niamoto_home, "config", "config.yml")

        if not os.path.exists(config_path):
            raise HTTPException(status_code=404, detail="Configuration file not found")

        # Read config file
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

        # Extract project information
        project_data = config_data.get("project", {})

        return ProjectInfo(
            name=project_data.get("name", "Niamoto Project"),
            version=project_data.get("version", "1.0.0"),
            niamoto_version=project_data.get("niamoto_version"),
            created_at=project_data.get("created_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to read project info: {str(e)}"
        )
