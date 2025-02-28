"""
Service for generating static content in Niamoto.
"""

from typing import List, Optional, Any, Dict

from rich.console import Console
from rich.progress import track
from sqlalchemy import asc
from sqlalchemy.sql import text

from niamoto.common.config import Config
from niamoto.common.exceptions import (
    GenerationError,
    TemplateError,
    OutputError,
    ValidationError,
    ConfigurationError,
    ProcessError,
)
from niamoto.common.utils import error_handler
from niamoto.core.components.exports.api_generator import ApiGenerator
from niamoto.core.components.exports.page_generator import PageGenerator
from niamoto.core.models import TaxonRef, PlotRef, ShapeRef
from niamoto.core.repositories.niamoto_repository import NiamotoRepository

console = Console()


class ExporterService:
    """Service to generate static pages and JSON files based on transforms configuration."""

    def __init__(self, config: Config):
        """
        Initialize the service.

        Args:
            config: Project configuration settings
        """
        self.config = config
        self.db_path = config.database_path
        self.page_generator = PageGenerator(config)
        self.api_generator = ApiGenerator(config)
        self.repository = NiamotoRepository(self.db_path)
        self.exports_config = config.get_exports_config()

    @error_handler(log=True, raise_error=True)
    def export_data(self, group: Optional[str] = None) -> None:
        """
        Export data according to configuration.

        Args:
            group: Optional group filter
        """
        try:
            # Load export configuration
            export_config = self.exports_config

            if not export_config:
                raise ConfigurationError(
                    "export.yml",
                    "No export configuration found",
                    details={"file": "export.yml"},
                )

            # Get available groups from config
            available_groups = []
            for config in export_config:
                if "group_by" in config and config["group_by"] not in available_groups:
                    available_groups.append(config["group_by"])

            # Validate group if specified
            if group and group not in available_groups:
                # Try case-insensitive match
                case_insensitive_match = next(
                    (g for g in available_groups if g.lower() == group.lower()), None
                )

                if case_insensitive_match:
                    # Use the correct case
                    group = case_insensitive_match
                    console.print(
                        f"[yellow]Using group '{group}' (case-insensitive match)[/yellow]"
                    )
                # Try singular/plural variants
                elif group.endswith("s") and group[:-1] in available_groups:
                    # Convert plural to singular
                    group = group[:-1]
                    console.print(
                        f"[yellow]Using singular form '{group}' instead of '{group}s'[/yellow]"
                    )
                elif f"{group}s" in available_groups:
                    # Convert singular to plural
                    group = f"{group}s"
                    console.print(
                        f"[yellow]Using plural form '{group}' instead of '{group[:-1]}'[/yellow]"
                    )
                else:
                    # Find closest match for suggestion
                    suggestion = ""
                    if available_groups:
                        import difflib

                        closest = difflib.get_close_matches(
                            group, available_groups, n=1
                        )
                        if closest:
                            suggestion = f" Did you mean '{closest[0]}'?"

                    raise ConfigurationError(
                        "export.yml",
                        f"No configuration found for group: {group}",
                        details={
                            "group": group,
                            "available_groups": available_groups,
                            "help": f"Available groups are: {', '.join(available_groups)}.{suggestion}",
                        },
                    )

            # Generate base static pages
            self._generate_static_pages()

            # Filter configuration by group
            configs = (
                [c for c in export_config if c.get("group_by") == group]
                if group
                else export_config
            )

            if group and not configs:
                raise ConfigurationError(
                    "export.yml",
                    f"No configuration found for group: {group}",
                    details={"group": group},
                )

            # Generate content for each group
            for group_config in configs:
                group_by = group_config.get("group_by")
                if group_by:
                    self._export_group_data(group_by, group_config)

            # Generate additional content
            self._generate_additional_content(group)

        except Exception as e:
            # Extract useful details from the original error if it's a ConfigurationError
            if isinstance(e, ConfigurationError) and hasattr(e, "details"):
                error_details = e.details.copy() if e.details else {}
                error_details.update({"group": group})

                raise ProcessError("Failed to export data", details=error_details)
            else:
                raise ProcessError(
                    "Failed to export data", details={"group": group, "error": str(e)}
                )

    @error_handler(log=True, raise_error=False)
    def _generate_static_pages(self) -> None:
        """
        Generate basic static pages.

        Raises:
            TemplateError: If template processing fails
            OutputError: If file generation fails
        """
        static_pages = [
            "index.html",
            "methodology.html",
            "resources.html",
            "construction.html",
            "trees.html",
            "plots.html",
            "forests.html",
        ]
        for page in static_pages:
            try:
                self.generate_page(page, page, depth="")
            except Exception as e:
                raise TemplateError(
                    page,
                    f"Failed to generate static page: {str(e)}",
                    details={"template": page},
                )

    @error_handler(log=True, raise_error=False)
    def _export_group_data(self, group_by: str, group_config: Dict[str, Any]) -> None:
        """
        Generate content for a specific group.

        Args:
            group_by: Type of group
            group_config: Configuration for the group

        Raises:
            GenerationError: If generation fails
        """
        try:
            entities = self._get_entities_for_group(group_by)

            for entity in track(entities, description=f"Generating {group_by} content"):
                stats = self._get_entity_stats(entity, group_by)
                if stats:
                    if group_by == "plot":
                        self._generate_page_for_plot(entity, stats, group_config)
                        self._generate_json_for_plot(entity, stats)
                    elif group_by == "shape":
                        self._generate_page_for_shape(entity, stats, group_config)
                        self._generate_json_for_shape(entity, stats)
                    elif group_by == "taxon":
                        self._generate_page_for_taxon(entity, stats, group_config)
                        self._generate_json_for_taxon(entity, stats)

        except Exception as e:
            raise GenerationError(
                f"Failed to generate content for {group_by}",
                details={"group": group_by, "error": str(e)},
            )

    @error_handler(log=True, raise_error=False)
    def _generate_additional_content(self, group: Optional[str] = None) -> None:
        """
        Generate additional required content.

        Args:
            group: Optional group filter

        Raises:
            GenerationError: If generation fails
        """
        try:
            if not group or group == "taxon":
                taxons = self._get_entities_for_group("taxon")
                self._generate_taxonomy_tree(taxons)
                self._generate_all_taxa_json(taxons)

            if not group or group == "plot":
                plots = self._get_entities_for_group("plot")
                self._generate_plot_list(plots)
                self._generate_all_plots_json(plots)

            if not group or group == "shape":
                shapes = self._get_entities_for_group("shape")
                self._generate_shape_list(shapes)
                self._generate_all_shapes_json(shapes)

        except Exception as e:
            raise GenerationError(
                "Failed to generate additional content",
                details={"group": group, "error": str(e)},
            )

    @error_handler(log=True, raise_error=False)
    def _get_entities_for_group(self, group_by: str) -> List[Any]:
        """
        Get filtered entities based on group type.

        Args:
            group_by: Type of group

        Returns:
            Filtered list of entities

        Raises:
            ValidationError: If group type is invalid
        """
        try:
            if group_by == "plot":
                entities = self.repository.get_entities(
                    PlotRef, order_by=asc(PlotRef.id)
                )
            elif group_by == "shape":
                entities = self.repository.get_entities(
                    ShapeRef, order_by=asc(ShapeRef.id)
                )
            elif group_by == "taxon":
                entities = self.repository.get_entities(
                    TaxonRef, order_by=asc(TaxonRef.full_name)
                )
            else:
                raise ValidationError("group_by", f"Unknown group type: {group_by}")

            return self._filter_entities_with_stats(entities, group_by)

        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise GenerationError(
                f"Failed to get entities for {group_by}", details={"error": str(e)}
            )

    @error_handler(log=True, raise_error=False)
    def _get_entity_stats(self, entity: Any, group_by: str) -> Optional[Dict]:
        """
        Get transforms for an entity.

        Args:
            entity: Entity to get stats for
            group_by: Type of group

        Returns:
            Entity transforms if available

        Raises:
            DatabaseError: If database query fails
        """
        try:
            with self.repository.db.engine.connect() as connection:
                result = connection.execute(
                    text(f"SELECT * FROM {group_by} WHERE {group_by}_id = :id"),
                    {"id": entity.id},
                )
                row = result.fetchone()
                return dict(zip(result.keys(), row)) if row else None
        except Exception as e:
            raise GenerationError(
                "Failed to get entity stats",
                details={"group": group_by, "entity_id": entity.id, "error": str(e)},
            )

    @error_handler(log=True, raise_error=False)
    def _filter_entities_with_stats(
        self, entities: List[Any], group_by: str
    ) -> List[Any]:
        """
        Filter entities to only include those with transforms.

        Args:
            entities: List of entities to filter
            group_by: Type of group

        Returns:
            Filtered list of entities

        Raises:
            GenerationError: If filtering fails
        """
        try:
            return [
                entity
                for entity in entities
                if self._get_entity_stats(entity, group_by) is not None
            ]
        except Exception as e:
            raise GenerationError(
                "Failed to filter entities",
                details={"group": group_by, "error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def generate_page(
        self,
        template_name: str,
        output_name: str,
        depth: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a page from a template.

        Args:
            template_name: Name of the template file
            output_name: Name of the output file
            depth: Relative path to root
            context: Template context variables

        Returns:
            Path of the generated page

        Raises:
            TemplateError: If template processing fails
            OutputError: If file generation fails
        """
        try:
            # Get context or create empty dict if None
            context = context or {}

            # Add first_ids to context
            context["first_ids"] = self.page_generator.get_first_ids()

            return self.page_generator.generate_page(
                template_name, output_name, depth, context
            )
        except Exception as e:
            if "template" in str(e).lower():
                raise TemplateError(
                    template_name,
                    f"Failed to process template: {str(e)}",
                    details={"output": output_name, "depth": depth},
                )
            raise OutputError(
                output_name,
                f"Failed to generate page: {str(e)}",
                details={"template": template_name, "depth": depth},
            )

    @error_handler(log=True, raise_error=False)
    def _generate_page_for_taxon(
        self, taxon: TaxonRef, stats: Optional[Any], mapping: Dict[Any, Any]
    ) -> str:
        """
        Generate a page for a specific taxon.

        Args:
            taxon: The taxon to generate for
            stats: Statistics to include
            mapping: Template mapping

        Returns:
            Generated page path

        Raises:
            TemplateError: If template processing fails
            OutputError: If file generation fails
        """
        try:
            return self.page_generator.generate_taxon_page(taxon, stats, mapping)
        except Exception as e:
            raise TemplateError(
                "taxon_template",
                f"Failed to generate taxon page: {str(e)}",
                details={"taxon_id": taxon.id, "taxon_name": taxon.full_name},
            )

    @error_handler(log=True, raise_error=False)
    def _generate_json_for_taxon(self, taxon: TaxonRef, stats: Optional[Any]) -> str:
        """
        Generate a JSON file for a taxon.

        Args:
            taxon: The taxon to generate for
            stats: Statistics to include

        Returns:
            Generated JSON file path

        Raises:
            OutputError: If file generation fails
        """
        try:
            return self.api_generator.generate_taxon_json(taxon, stats)
        except Exception as e:
            raise OutputError(
                f"taxon_{taxon.id}.json",
                f"Failed to generate taxon JSON: {str(e)}",
                details={"taxon_id": taxon.id, "taxon_name": taxon.full_name},
            )

    @error_handler(log=True, raise_error=False)
    def _generate_taxonomy_tree(self, taxons: List[TaxonRef]) -> None:
        """
        Generate a taxonomy tree.

        Args:
            taxons: List of taxons

        Raises:
            GenerationError: If tree generation fails
        """
        try:
            self.page_generator.generate_taxonomy_tree_js(taxons)
        except Exception as e:
            raise GenerationError(
                "Failed to generate taxonomy tree",
                details={"taxon_count": len(taxons), "error": str(e)},
            )

    @error_handler(log=True, raise_error=False)
    def _generate_plot_list(self, plots: List[PlotRef]) -> None:
        """
        Generate a list of plots.

        Args:
            plots: List of plots

        Raises:
            GenerationError: If list generation fails
        """
        try:
            self.page_generator.generate_plot_list_js(plots)
        except Exception as e:
            raise GenerationError(
                "Failed to generate plot list",
                details={"plot_count": len(plots), "error": str(e)},
            )

    @error_handler(log=True, raise_error=False)
    def _generate_page_for_plot(
        self, plot: PlotRef, stats: Optional[Any], mapping: Dict[Any, Any]
    ) -> str:
        """
        Generate a page for a plot.

        Args:
            plot: The plot to generate for
            stats: Statistics to include
            mapping: Template mapping

        Returns:
            Generated page path

        Raises:
            TemplateError: If template processing fails
            OutputError: If file generation fails
        """
        try:
            return self.page_generator.generate_plot_page(plot, stats, mapping)
        except Exception as e:
            raise TemplateError(
                "plot_template",
                f"Failed to generate plot page: {str(e)}",
                details={"plot_id": plot.id, "plot_name": plot.locality},
            )

    @error_handler(log=True, raise_error=False)
    def _generate_json_for_plot(self, plot: PlotRef, stats: Optional[Any]) -> str:
        """
        Generate a JSON file for a plot.

        Args:
            plot: The plot to generate for
            stats: Statistics to include

        Returns:
            Generated JSON file path

        Raises:
            OutputError: If file generation fails
        """
        try:
            return self.api_generator.generate_plot_json(plot, stats)
        except Exception as e:
            raise OutputError(
                f"plot_{plot.id}.json",
                f"Failed to generate plot JSON: {str(e)}",
                details={"plot_id": plot.id, "plot_name": plot.locality},
            )

    @error_handler(log=True, raise_error=False)
    def _generate_shape_list(self, shapes: List[ShapeRef]) -> None:
        """
        Generate a list of shapes.

        Args:
            shapes: List of shapes

        Raises:
            GenerationError: If list generation fails
        """
        try:
            self.page_generator.generate_shape_list_js(shapes)
        except Exception as e:
            raise GenerationError(
                "Failed to generate shape list",
                details={"shape_count": len(shapes), "error": str(e)},
            )

    @error_handler(log=True, raise_error=False)
    def _generate_page_for_shape(
        self, shape: ShapeRef, stats: Optional[Any], mapping: Dict[Any, Any]
    ) -> str:
        """
        Generate a page for a shape.

        Args:
            shape: The shape to generate for
            stats: Statistics to include
            mapping: Template mapping

        Returns:
            Generated page path

        Raises:
            TemplateError: If template processing fails
            OutputError: If file generation fails
        """
        try:
            return self.page_generator.generate_shape_page(shape, stats, mapping)
        except Exception as e:
            raise TemplateError(
                "shape_template",
                f"Failed to generate shape page: {str(e)}",
                details={"shape_id": shape.id, "shape_name": shape.label},
            )

    @error_handler(log=True, raise_error=False)
    def _generate_json_for_shape(self, shape: ShapeRef, stats: Optional[Any]) -> str:
        """
        Generate a JSON file for a shape.

        Args:
            shape: The shape to generate for
            stats: Statistics to include

        Returns:
            Generated JSON file path

        Raises:
            OutputError: If file generation fails
        """
        try:
            return self.api_generator.generate_shape_json(shape, stats)
        except Exception as e:
            raise OutputError(
                f"shape_{shape.id}.json",
                f"Failed to generate shape JSON: {str(e)}",
                details={"shape_id": shape.id, "shape_name": shape.label},
            )

    @error_handler(log=True, raise_error=False)
    def _generate_all_plots_json(self, plots: List[PlotRef]) -> None:
        """
        Generate a JSON file for all plots.

        Args:
            plots: List of plots

        Raises:
            OutputError: If file generation fails
        """
        try:
            self.api_generator.generate_all_plots_json(plots)
        except Exception as e:
            raise OutputError(
                "all_plots.json",
                f"Failed to generate all plots JSON: {str(e)}",
                details={"plot_count": len(plots)},
            )

    @error_handler(log=True, raise_error=False)
    def _generate_all_shapes_json(self, shapes: List[ShapeRef]) -> None:
        """
        Generate a JSON file for all shapes.

        Args:
            shapes: List of shapes

        Raises:
            OutputError: If file generation fails
        """
        try:
            self.api_generator.generate_all_shapes_json(shapes)
        except Exception as e:
            raise OutputError(
                "all_shapes.json",
                f"Failed to generate all shapes JSON: {str(e)}",
                details={"shape_count": len(shapes)},
            )

    @error_handler(log=True, raise_error=False)
    def _generate_all_taxa_json(self, taxons: List[TaxonRef]) -> None:
        """
        Generate a JSON file for all taxons.

        Args:
            taxons: List of taxons

        Raises:
            OutputError: If file generation fails
        """
        try:
            self.api_generator.generate_all_taxa_json(taxons)
        except Exception as e:
            raise OutputError(
                "all_taxa.json",
                f"Failed to generate all taxa JSON: {str(e)}",
                details={"taxon_count": len(taxons)},
            )
