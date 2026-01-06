"""
Dynamic widget generator based on column data types.

This module generates widget suggestions dynamically based on:
1. Column data category (numeric, categorical, boolean, geographic)
2. Column statistics (min, max, cardinality, null ratio)
3. Compatible plugins for each data type - discovered via SmartMatcher

The SmartMatcher uses output_structure/compatible_structures declared on plugins
to automatically find compatible transformer→widget pairs. This enables user-created
plugins to be automatically discoverable by the smart setup wizard.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from niamoto.core.imports.data_analyzer import (
    DataCategory,
    EnrichedColumnProfile,
    FieldPurpose,
)
from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.matching.matcher import SmartMatcher

logger = logging.getLogger(__name__)


@dataclass
class WidgetSuggestion:
    """A dynamically generated widget suggestion.

    Now includes both transformer and widget plugin information,
    reflecting the full data flow: column → transformer → widget.
    """

    id: str  # Unique ID: {column}_{transformer}_{widget}
    name: str
    description: str
    transformer_plugin: str  # Plugin that transforms the data
    widget_plugin: str  # Plugin that renders the visualization
    widget_type: str  # distribution, max, mean, map, donut, etc.
    category: str  # chart, gauge, map, donut, info
    icon: str
    column: str  # Source column name
    confidence: float
    transformer_config: Dict[str, Any]  # Config for transformer
    widget_config: Dict[str, Any]  # Config for widget
    source_name: str  # Source dataset name (from import.yml)
    is_primary: bool = True  # Primary suggestion for this column
    alternatives: List[str] = field(default_factory=list)  # Alternative widget IDs
    match_score: float = 1.0  # SmartMatcher compatibility score

    @property
    def plugin(self) -> str:
        """Backward compatibility: returns transformer plugin."""
        return self.transformer_plugin

    @property
    def config(self) -> Dict[str, Any]:
        """Backward compatibility: returns transformer config."""
        return self.transformer_config

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            "template_id": self.id,
            "name": self.name,
            "description": self.description,
            "transformer_plugin": self.transformer_plugin,
            "widget_plugin": self.widget_plugin,
            "plugin": self.transformer_plugin,  # backward compat
            "category": self.category,
            "icon": self.icon,
            "confidence": round(self.confidence, 2),
            "source": "auto",
            "matched_column": self.column,
            "match_reason": f"Colonne '{self.column}' de type {self.widget_type}",
            "is_recommended": self.is_primary,
            "transformer_config": self.transformer_config,
            "widget_config": self.widget_config,
            "config": self.transformer_config,  # backward compat
            "alternatives": self.alternatives,
            "match_score": self.match_score,
        }


class WidgetGenerator:
    """
    Generates widget suggestions dynamically based on column profiles.

    Uses SmartMatcher for automatic transformer→widget discovery based on
    output_structure/compatible_structures declared on plugins.

    For each column, suggests compatible visualizations based on data type:
    - NUMERIC_CONTINUOUS: distribution (histogram), max, mean, min gauges
    - NUMERIC_DISCRETE: distribution, count stats
    - CATEGORICAL: categorical distribution (bar chart)
    - BOOLEAN: binary counter (donut)
    - GEOGRAPHIC: map
    - CATEGORICAL_HIGH_CARD: top ranking

    The transformer→widget mapping is discovered automatically via SmartMatcher,
    enabling user-created plugins to be automatically used by the smart setup.
    """

    # Transformers suitable for each data category
    # This is domain knowledge: numeric continuous data → histogram transformer
    TRANSFORMERS_BY_CATEGORY: Dict[DataCategory, List[str]] = {
        DataCategory.NUMERIC_CONTINUOUS: ["binned_distribution", "statistical_summary"],
        DataCategory.NUMERIC_DISCRETE: ["binned_distribution", "statistical_summary"],
        # Both categorical types get both transformers - user can choose
        DataCategory.CATEGORICAL: ["categorical_distribution", "top_ranking"],
        DataCategory.CATEGORICAL_HIGH_CARD: ["top_ranking", "categorical_distribution"],
        DataCategory.BOOLEAN: ["binary_counter"],
        DataCategory.GEOGRAPHIC: ["geospatial_extractor"],
        DataCategory.TEMPORAL: ["time_series_analysis"],
        DataCategory.IDENTIFIER: [],  # Skip IDs
        DataCategory.TEXT: [],  # Skip text
    }

    # Primary transformer per data category (shown first)
    PRIMARY_TRANSFORMER = {
        DataCategory.NUMERIC_CONTINUOUS: "binned_distribution",
        DataCategory.NUMERIC_DISCRETE: "binned_distribution",
        DataCategory.CATEGORICAL: "categorical_distribution",
        DataCategory.CATEGORICAL_HIGH_CARD: "top_ranking",
        DataCategory.BOOLEAN: "binary_counter",
        DataCategory.GEOGRAPHIC: "geospatial_extractor",
        DataCategory.TEMPORAL: "time_series_analysis",
    }

    # Widget type labels for display (widget_plugin → display info)
    WIDGET_INFO = {
        "bar_plot": {"type": "distribution", "category": "chart", "icon": "BarChart3"},
        "radial_gauge": {"type": "gauge", "category": "gauge", "icon": "Activity"},
        "donut_chart": {"type": "donut", "category": "donut", "icon": "PieChart"},
        "interactive_map": {"type": "map", "category": "map", "icon": "Map"},
        "info_grid": {"type": "info", "category": "info", "icon": "Info"},
        "hierarchical_nav_widget": {
            "type": "navigation",
            "category": "navigation",
            "icon": "FolderTree",
        },
    }

    # Default fallback for unknown widgets
    DEFAULT_WIDGET_INFO = {"type": "chart", "category": "chart", "icon": "BarChart3"}

    def __init__(self):
        """Initialize the widget generator with SmartMatcher."""
        self.matcher = SmartMatcher()
        # Cache for transformer→widget mappings (computed once)
        self._widget_cache: Dict[str, List[Tuple[str, float]]] = {}

    def generate_for_columns(
        self,
        profiles: List[EnrichedColumnProfile],
        source_table: str = "occurrences",
    ) -> List[WidgetSuggestion]:
        """
        Generate widget suggestions for a list of column profiles.

        Uses SmartMatcher to automatically discover compatible widgets
        for each transformer based on output_structure/compatible_structures.

        Args:
            profiles: Enriched column profiles from data analysis
            source_table: Source table name for configs

        Returns:
            List of WidgetSuggestion sorted by confidence
        """
        all_suggestions: List[WidgetSuggestion] = []

        for profile in profiles:
            if profile.data_category is None:
                continue

            suggestions = self._generate_for_column(profile, source_table)
            all_suggestions.extend(suggestions)

        # Sort by confidence, then by primary status
        all_suggestions.sort(key=lambda s: (-s.confidence, not s.is_primary, s.name))

        return all_suggestions

    def _generate_for_column(
        self,
        profile: EnrichedColumnProfile,
        source_table: str,
    ) -> List[WidgetSuggestion]:
        """
        Generate all compatible widgets for a single column.

        Uses SmartMatcher for automatic transformer→widget discovery.
        """
        if profile.data_category is None:
            return []

        # Get transformers suitable for this data category
        transformer_names = self.TRANSFORMERS_BY_CATEGORY.get(profile.data_category, [])
        if not transformer_names:
            return []

        suggestions = []
        primary_transformer = self.PRIMARY_TRANSFORMER.get(profile.data_category)

        # For each compatible transformer, find compatible widgets via SmartMatcher
        for transformer_name in transformer_names:
            is_primary = transformer_name == primary_transformer

            # Get compatible widgets via SmartMatcher
            compatible_widgets = self._get_compatible_widgets(transformer_name)

            if not compatible_widgets:
                logger.debug(
                    f"No compatible widgets found for transformer {transformer_name}"
                )
                continue

            # Create suggestions for each transformer+widget pair
            for widget_name, match_score in compatible_widgets:
                suggestion = self._create_suggestion(
                    profile=profile,
                    transformer_name=transformer_name,
                    widget_name=widget_name,
                    source_table=source_table,
                    is_primary=is_primary,
                    match_score=match_score,
                )
                if suggestion:
                    suggestions.append(suggestion)

        # Link alternatives (other suggestions for same column)
        suggestion_ids = [s.id for s in suggestions]
        for suggestion in suggestions:
            suggestion.alternatives = [
                sid for sid in suggestion_ids if sid != suggestion.id
            ]

        return suggestions

    def _get_compatible_widgets(self, transformer_name: str) -> List[Tuple[str, float]]:
        """
        Get compatible widgets for a transformer using SmartMatcher.

        Results are cached for performance.

        Args:
            transformer_name: Name of the transformer plugin

        Returns:
            List of (widget_name, match_score) tuples
        """
        if transformer_name in self._widget_cache:
            return self._widget_cache[transformer_name]

        try:
            # Get transformer class from registry
            transformer_class = PluginRegistry.get_plugin(
                transformer_name, PluginType.TRANSFORMER
            )

            # Use SmartMatcher to find compatible widgets
            widget_suggestions = self.matcher.find_compatible_widgets(transformer_class)

            # Extract widget names and scores
            results = [(ws.widget_name, ws.score) for ws in widget_suggestions]

            # Cache results
            self._widget_cache[transformer_name] = results

            logger.debug(
                f"SmartMatcher found {len(results)} compatible widgets for {transformer_name}: "
                f"{[r[0] for r in results]}"
            )

            return results

        except Exception as e:
            logger.warning(
                f"Error finding compatible widgets for {transformer_name}: {e}"
            )
            return []

    def _create_suggestion(
        self,
        profile: EnrichedColumnProfile,
        transformer_name: str,
        widget_name: str,
        source_table: str,
        is_primary: bool,
        match_score: float,
    ) -> Optional[WidgetSuggestion]:
        """
        Create a single widget suggestion with both transformer and widget info.

        Args:
            profile: Column profile
            transformer_name: Name of transformer plugin
            widget_name: Name of widget plugin
            source_table: Source table name
            is_primary: Whether this is the primary suggestion
            match_score: SmartMatcher compatibility score

        Returns:
            WidgetSuggestion or None if config cannot be generated
        """
        # Generate transformer config based on column stats
        transformer_config = self._generate_transformer_config(
            profile, transformer_name, source_table
        )
        if transformer_config is None:
            return None

        # Generate widget config (field mappings, etc.)
        widget_config = self._generate_widget_config(
            profile, transformer_name, widget_name
        )

        # Get widget display info
        widget_info = self.WIDGET_INFO.get(widget_name, self.DEFAULT_WIDGET_INFO)

        # Calculate confidence based on data quality and match score
        confidence = self._calculate_confidence(
            profile, transformer_name, is_primary, match_score
        )

        # Generate human-readable name and description
        name, description = self._generate_labels(
            profile, transformer_name, widget_name
        )

        return WidgetSuggestion(
            id=f"{profile.name}_{transformer_name}_{widget_name}",
            name=name,
            description=description,
            transformer_plugin=transformer_name,
            widget_plugin=widget_name,
            widget_type=widget_info["type"],
            category=widget_info["category"],
            icon=widget_info["icon"],
            column=profile.name,
            confidence=confidence,
            transformer_config=transformer_config,
            widget_config=widget_config,
            source_name=source_table,
            is_primary=is_primary,
            match_score=match_score,
        )

    def _generate_transformer_config(
        self,
        profile: EnrichedColumnProfile,
        transformer_name: str,
        source_table: str,
    ) -> Optional[Dict[str, Any]]:
        """Generate transformer plugin config based on column stats."""

        if transformer_name == "binned_distribution":
            return self._config_distribution(profile, source_table)
        elif transformer_name == "statistical_summary":
            return self._config_stats(profile, source_table)
        elif transformer_name == "categorical_distribution":
            return self._config_categorical(profile, source_table)
        elif transformer_name == "top_ranking":
            return self._config_top_ranking(profile, source_table)
        elif transformer_name == "binary_counter":
            return self._config_binary(profile, source_table)
        elif transformer_name == "geospatial_extractor":
            return self._config_map(profile, source_table)
        elif transformer_name == "time_series_analysis":
            return self._config_time_series(profile, source_table)

        # Try to generate a generic config for unknown transformers
        logger.debug(
            f"No specific config generator for {transformer_name}, using generic"
        )
        return {
            "source": source_table,
            "field": profile.name,
        }

    def _generate_widget_config(
        self,
        profile: EnrichedColumnProfile,
        transformer_name: str,
        widget_name: str,
    ) -> Dict[str, Any]:
        """
        Generate widget config with field mappings.

        This maps the transformer output fields to the widget input fields.
        """
        # Common widget configs based on transformer→widget pair
        if transformer_name == "binned_distribution" and widget_name == "bar_plot":
            return {
                "x_axis": "bin",
                "y_axis": "count",
                "field_mapping": {"bins": "bin", "counts": "count"},
                "transform": "bins_to_df",
            }
        elif (
            transformer_name == "categorical_distribution" and widget_name == "bar_plot"
        ):
            return {
                "x_axis": "category_label",
                "y_axis": "value",
                "transform": "category_with_labels",
            }
        elif (
            transformer_name == "statistical_summary" and widget_name == "radial_gauge"
        ):
            return {
                "value_field": "value",
                "max_field": "max_value",
            }
        elif transformer_name == "binary_counter" and widget_name == "donut_chart":
            return {
                "labels_field": "labels",
                "values_field": "values",
            }
        elif (
            transformer_name == "geospatial_extractor"
            and widget_name == "interactive_map"
        ):
            return {
                "geojson_field": "features",
            }
        elif transformer_name == "top_ranking" and widget_name == "bar_plot":
            return {
                "x_axis": "label",
                "y_axis": "count",
                "orientation": "h",
            }

        # Default empty config for unknown combinations
        return {}

    def _config_time_series(
        self, profile: EnrichedColumnProfile, source_table: str
    ) -> Dict[str, Any]:
        """Generate time_series_analysis config."""
        return {
            "source": source_table,
            "field": profile.name,
            "output_type": "monthly",
        }

    def _config_distribution(
        self, profile: EnrichedColumnProfile, source_table: str
    ) -> Optional[Dict[str, Any]]:
        """Generate binned_distribution config with smart bins."""
        # Use suggested_bins if available, otherwise generate from value_range
        if profile.suggested_bins:
            bins = profile.suggested_bins
        elif profile.value_range:
            min_val, max_val = profile.value_range
            bins = self._generate_smart_bins(min_val, max_val)
        else:
            bins = [0, 10, 20, 30, 40, 50, 100, 200, 500]

        # Generate axis labels
        unit = self._guess_unit(profile.name)
        x_label = profile.name.upper()
        if unit:
            x_label = f"{x_label} ({unit})"

        # Default to percentage since include_percentages is True
        y_label = "%"

        return {
            "source": source_table,
            "field": profile.name,
            "bins": bins,
            "include_percentages": True,
            "x_label": x_label,
            "y_label": y_label,
        }

    def _config_stats(
        self, profile: EnrichedColumnProfile, source_table: str
    ) -> Dict[str, Any]:
        """Generate statistical_summary config."""
        # Get max from value_range if available
        if profile.value_range:
            _, max_val = profile.value_range
        else:
            max_val = 100

        # Estimate max_value for gauge (round up to nice number)
        gauge_max = self._round_to_nice_number(max_val * 1.2)

        # Guess unit from column name
        unit = self._guess_unit(profile.name)

        # Generate all useful stats
        return {
            "source": source_table,
            "field": profile.name,
            "stats": ["max", "mean", "min"],
            "units": unit,
            "max_value": gauge_max,
        }

    def _config_categorical(
        self, profile: EnrichedColumnProfile, source_table: str
    ) -> Optional[Dict[str, Any]]:
        """Generate categorical_distribution config."""
        if not profile.sample_values:
            return None

        # Use sample values as categories
        categories = list(profile.sample_values)[:10]

        return {
            "source": source_table,
            "field": profile.name,
            "categories": categories,
            "include_percentages": True,
        }

    def _config_top_ranking(
        self, profile: EnrichedColumnProfile, source_table: str
    ) -> Dict[str, Any]:
        """Generate top_ranking config."""
        return {
            "source": source_table,
            "field": profile.name,
            "mode": "direct",
            "count": 10,
        }

    def _config_binary(
        self, profile: EnrichedColumnProfile, source_table: str
    ) -> Dict[str, Any]:
        """Generate binary_counter config."""
        # Try to guess labels from column name
        true_label, false_label = self._guess_binary_labels(profile.name)

        return {
            "source": source_table,
            "field": profile.name,
            "true_label": true_label,
            "false_label": false_label,
            "include_percentages": True,
        }

    def _config_map(
        self, profile: EnrichedColumnProfile, source_table: str
    ) -> Dict[str, Any]:
        """Generate geospatial_extractor config."""
        return {
            "source": source_table,
            "field": profile.name,
            "format": "geojson",
            "group_by_coordinates": True,
        }

    def _generate_smart_bins(self, min_val: float, max_val: float) -> List[float]:
        """Generate smart histogram bins based on data range."""
        if max_val <= min_val:
            return [0, 10, 20, 30, 40, 50]

        range_val = max_val - min_val

        # Determine step size based on range
        if range_val <= 10:
            step = 1
        elif range_val <= 50:
            step = 5
        elif range_val <= 100:
            step = 10
        elif range_val <= 500:
            step = 50
        elif range_val <= 2000:
            step = 100
        else:
            step = 500

        # Round min down and max up to step
        start = math.floor(min_val / step) * step
        end = math.ceil(max_val / step) * step

        bins = []
        current = start
        while current <= end:
            bins.append(current)
            current += step

        # Limit to ~15 bins max
        while len(bins) > 15:
            bins = bins[::2]

        return bins

    def _round_to_nice_number(self, value: float) -> float:
        """Round to a nice number for gauge max values."""
        if value <= 0:
            return 100

        magnitude = 10 ** math.floor(math.log10(value))
        normalized = value / magnitude

        if normalized <= 1:
            nice = 1
        elif normalized <= 2:
            nice = 2
        elif normalized <= 5:
            nice = 5
        else:
            nice = 10

        return nice * magnitude

    def _guess_unit(self, column_name: str) -> str:
        """Guess measurement unit from column name."""
        name_lower = column_name.lower()

        unit_map = {
            "height": "m",
            "hauteur": "m",
            "elevation": "m",
            "altitude": "m",
            "dbh": "cm",
            "diameter": "cm",
            "rainfall": "mm",
            "precipitation": "mm",
            "temperature": "°C",
            "area": "m²",
            "surface": "m²",
            "density": "g/cm³",
            "thickness": "mm",
            "weight": "kg",
            "mass": "kg",
        }

        for pattern, unit in unit_map.items():
            if pattern in name_lower:
                return unit

        return ""

    def _guess_binary_labels(self, column_name: str) -> Tuple[str, str]:
        """Guess labels for binary columns."""
        name_lower = column_name.lower()

        # Common patterns
        if "um" in name_lower or "ultramafique" in name_lower:
            return ("UM", "NUM")
        if "endemic" in name_lower or "endemique" in name_lower:
            return ("Endémique", "Non endémique")
        if "protected" in name_lower or "protege" in name_lower:
            return ("Protégé", "Non protégé")
        if "native" in name_lower:
            return ("Natif", "Introduit")

        # Default
        return ("Oui", "Non")

    def _generate_labels(
        self, profile: EnrichedColumnProfile, transformer_name: str, widget_name: str
    ) -> Tuple[str, str]:
        """Generate human-readable name and description based on transformer+widget."""
        col_name = profile.name.replace("_", " ").title()

        # Labels based on transformer (determines data processing)
        transformer_labels = {
            "binned_distribution": (
                f"Distribution de {col_name}",
                f"Histogramme de la distribution de {profile.name}",
            ),
            "statistical_summary": (
                f"Statistiques de {col_name}",
                f"Valeurs statistiques de {profile.name}",
            ),
            "categorical_distribution": (
                f"Répartition par {col_name}",
                f"Distribution catégorielle de {profile.name}",
            ),
            "top_ranking": (
                f"Top {col_name}",
                f"Classement des valeurs les plus fréquentes de {profile.name}",
            ),
            "binary_counter": (
                f"Distribution {col_name}",
                f"Répartition binaire de {profile.name}",
            ),
            "geospatial_extractor": (
                f"Carte {col_name}",
                f"Visualisation géographique de {profile.name}",
            ),
            "time_series_analysis": (
                f"Évolution temporelle {col_name}",
                f"Analyse temporelle de {profile.name}",
            ),
        }

        return transformer_labels.get(
            transformer_name, (col_name, f"Widget {widget_name} pour {profile.name}")
        )

    def _calculate_confidence(
        self,
        profile: EnrichedColumnProfile,
        transformer_name: str,
        is_primary: bool,
        match_score: float,
    ) -> float:
        """
        Calculate confidence score based on data quality and field purpose.

        All transformers applicable to a data category should be proposed together.
        If bar_plot is proposed for a numeric column, gauge should be too.

        Fields are prioritized by their purpose:
        - MEASUREMENT fields (dbh, elevation): highest priority
        - CLASSIFICATION fields (family, genus): normal priority
        - FOREIGN_KEY/PRIMARY_KEY: low priority (IDs aren't meaningful to visualize)

        Args:
            profile: Column profile
            transformer_name: Name of transformer plugin
            is_primary: Whether this is the primary transformer for data category
            match_score: SmartMatcher compatibility score (0-1)

        Returns:
            Confidence score (0.3-1.0)
        """
        # Base confidence: same for all transformers of the same category
        base_confidence = 0.70

        # Factor in SmartMatcher score (proportional, not multiplicative)
        base_confidence += (match_score - 0.5) * 0.2  # Range: -0.1 to +0.1

        # Penalize high null ratio proportionally (max 15% penalty)
        if profile.null_ratio > 0:
            base_confidence -= profile.null_ratio * 0.15

        # Small boost for primary transformers (for ordering, not filtering)
        if is_primary:
            base_confidence += 0.05

        # Boost for common/useful transformer types
        if transformer_name in ("binned_distribution", "geospatial_extractor"):
            base_confidence += 0.03

        # === Field purpose penalties ===
        # Foreign keys and primary keys are technical fields, not meaningful to visualize
        if profile.field_purpose in (
            FieldPurpose.FOREIGN_KEY,
            FieldPurpose.PRIMARY_KEY,
        ):
            base_confidence -= 0.25

        # Identifiers (even if not detected as FK/PK) should be penalized
        if profile.data_category == DataCategory.IDENTIFIER:
            base_confidence -= 0.20

        # Column names containing 'id_' or '_id' are likely identifiers
        col_name_lower = profile.name.lower()
        if col_name_lower.startswith("id_") or col_name_lower.endswith("_id"):
            base_confidence -= 0.10

        return min(1.0, max(0.3, base_confidence))

    @staticmethod
    def generate_navigation_suggestion(
        reference_name: str,
        is_hierarchical: bool,
        hierarchy_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a navigation widget suggestion for a reference.

        The hierarchical_nav_widget adapts its behavior based on the reference type:
        - Hierarchical (taxons): Uses nested set (lft/rght) for tree navigation
        - Flat (plots): Simple list navigation without hierarchy

        Args:
            reference_name: Name of the reference (e.g., 'taxons', 'plots')
            is_hierarchical: Whether the reference has hierarchy structure
            hierarchy_fields: Dict with detected hierarchy fields (from HierarchyFields)

        Returns:
            Dict in TemplateSuggestion format for the navigation widget
        """
        # Default field values
        fields = hierarchy_fields or {}
        id_field = fields.get("id_field", "id")
        name_field = fields.get("name_field", "name")

        # Build widget config based on hierarchy type
        widget_config: Dict[str, Any] = {
            "referential_data": reference_name,
            "id_field": id_field,
            "name_field": name_field,
            "base_url": f"{{{{ depth }}}}{reference_name}/",
            "show_search": True,
        }

        # Add hierarchy-specific fields if available
        if is_hierarchical:
            if fields.get("has_nested_set"):
                widget_config["lft_field"] = fields.get("lft_field", "lft")
                widget_config["rght_field"] = fields.get("rght_field", "rght")
            if fields.get("has_level"):
                widget_config["level_field"] = fields.get("level_field", "level")
            if fields.get("has_parent"):
                widget_config["parent_id_field"] = fields.get(
                    "parent_id_field", "parent_id"
                )

        # Generate human-readable name
        ref_label = reference_name.replace("_", " ").title()
        if is_hierarchical:
            name = f"Navigation {ref_label}"
            description = (
                f"Arborescence hiérarchique de navigation pour {reference_name}"
            )
        else:
            name = f"Liste {ref_label}"
            description = f"Liste de navigation pour {reference_name}"

        return {
            "template_id": f"{reference_name}_hierarchical_nav_widget",
            "name": name,
            "description": description,
            "plugin": "hierarchical_nav_widget",
            "category": "navigation",
            "icon": "FolderTree",
            "confidence": 0.95,  # High confidence - always applicable
            "source": "auto",
            "source_name": reference_name,
            "matched_column": reference_name,  # The reference itself
            "match_reason": f"Widget de navigation pour la référence '{reference_name}'",
            "is_recommended": True,
            "config": widget_config,
            "alternatives": [],
        }
