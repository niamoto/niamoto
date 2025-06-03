"""Data access utilities for widgets and exporters."""

from typing import Any, Dict, Optional
import logging

import pandas as pd

logger = logging.getLogger(__name__)


def get_nested_data(data: Dict, key_path: str) -> Any:
    """Access nested dictionary data using dot notation.

    Args:
        data: The dictionary to access
        key_path: Path to the data using dot notation (e.g., 'meff.value')

    Returns:
        The value at the specified path or None if not found
    """
    if not key_path or not isinstance(data, dict):
        return None

    parts = key_path.split(".")
    current = data

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    return current


def convert_to_dataframe(
    data: Any,
    x_field: str,
    y_field: str,
    color_field: Optional[str] = None,
    mapping: Optional[Dict[str, str]] = None,
) -> Optional[pd.DataFrame]:
    """Convert various data structures to a DataFrame suitable for plotting.

    Args:
        data: Input data (dictionary, list, etc.)
        x_field: Field name for x-axis values
        y_field: Field name for y-axis values
        color_field: Optional field name for color/category
        mapping: Optional mapping of input field names to output column names

    Returns:
        Pandas DataFrame or None if conversion fails
    """
    # Initialize result
    df = None

    # Case 1: Already a DataFrame
    if isinstance(data, pd.DataFrame):
        df = data.copy()

    # Case 2: Dict with direct keys for x and y fields
    elif isinstance(data, dict):
        # Try to extract data using the field names as direct keys
        x_data = None
        y_data = None
        color_data = None

        # Try nested access first
        if "." in x_field:
            x_data = get_nested_data(data, x_field)
        elif x_field in data:
            x_data = data[x_field]

        if "." in y_field:
            y_data = get_nested_data(data, y_field)
        elif y_field in data:
            y_data = data[y_field]

        if color_field:
            if "." in color_field:
                color_data = get_nested_data(data, color_field)
            elif color_field in data:
                color_data = data[color_field]

        # If we have both x and y data, create a DataFrame
        if x_data is not None and y_data is not None:
            if (
                isinstance(x_data, list)
                and isinstance(y_data, list)
                and len(x_data) == len(y_data)
            ):
                df_data = {x_field: x_data, y_field: y_data}

                # Add color field if available and matching length
                if (
                    color_data is not None
                    and isinstance(color_data, list)
                    and len(color_data) == len(x_data)
                ):
                    df_data[color_field] = color_data

                df = pd.DataFrame(df_data)

    # Case 3: List of dicts
    elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
        try:
            df = pd.DataFrame(data)
        except Exception:
            pass

    # Apply column mapping if provided
    if df is not None and mapping:
        df = df.rename(columns=mapping)

    return df


def transform_data(
    data: Any, transform_type: str, transform_params: Dict[str, Any] = None
) -> Any:
    """Transform data according to specified transformation.

    Args:
        data: Input data to transform
        transform_type: Type of transformation to apply
        transform_params: Parameters for the transformation

    Returns:
        Transformed data
    """
    params = transform_params or {}

    # Long to wide format transformation
    if transform_type == "unpivot":
        id_vars = params.get("id_vars", [])
        value_vars = params.get("value_vars", [])
        var_name = params.get("var_name", "variable")
        value_name = params.get("value_name", "value")

        if isinstance(data, pd.DataFrame):
            return pd.melt(
                data,
                id_vars=id_vars,
                value_vars=value_vars,
                var_name=var_name,
                value_name=value_name,
            )

    # Wide to long format transformation
    elif transform_type == "pivot":
        index = params.get("index")
        columns = params.get("columns")
        values = params.get("values")

        if isinstance(data, pd.DataFrame) and index and columns and values:
            return data.pivot(index=index, columns=columns, values=values)

    # Extract series from dict structure
    elif transform_type == "extract_series":
        x_field = params.get("x_field")
        series_field = params.get("series_field")
        categories = params.get("categories", [])

        # Case 1: Standard structure with direct fields for both x and series
        if isinstance(data, dict) and x_field in data and series_field in data:
            if isinstance(data[x_field], list) and isinstance(data[series_field], dict):
                result_df = pd.DataFrame({x_field: data[x_field]})

                for category in categories:
                    if category in data[series_field]:
                        result_df[category] = data[series_field][category]

                return result_df

        # Case 2: Structure like forest types by altitude where keys are direct
        elif isinstance(data, dict) and x_field in data:
            if all(cat in data for cat in categories):
                result_df = pd.DataFrame({x_field: data[x_field]})

                for category in categories:
                    if category in data and isinstance(data[category], list):
                        if len(data[category]) == len(data[x_field]):
                            result_df[category] = data[category]

                if len(result_df.columns) > 1:  # At least one category column added
                    return result_df

    # Transformation spécifique pour les dictionnaires imbriqués type Holdridge
    elif transform_type == "nested_dict_to_long":
        primary_keys = params.get("primary_keys", [])
        category_field = params.get("category_field", "category")
        value_field = params.get("value_field", "value")
        type_field = params.get("type_field", "type")

        if isinstance(data, dict) and all(key in data for key in primary_keys):
            rows = []

            # Parcourir chaque dictionnaire primaire (ex: forest, non_forest)
            for primary_key in primary_keys:
                primary_dict = data[primary_key]
                if isinstance(primary_dict, dict):
                    # Extraire les valeurs pour chaque catégorie
                    for category, value in primary_dict.items():
                        rows.append(
                            {
                                category_field: category,
                                value_field: value,
                                type_field: primary_key,
                            }
                        )

            if rows:
                return pd.DataFrame(rows)

    # Transformation générique pour extraire une série de données avec classes
    elif transform_type == "extract_single_series":
        class_field = params.get("class_field", "class_name")
        series_field = params.get("series_field", "series")
        series_key = params.get("series_key")
        class_suffix = params.get(
            "class_suffix", ""
        )  # Pour ajouter un suffixe aux classes
        value_label = params.get("value_label", "values")
        class_label = params.get("class_label", "class_name")

        if isinstance(data, dict) and class_field in data:
            # Cas où les données sont dans la structure attendue
            if series_field in data and isinstance(data[series_field], dict):
                classes = data[class_field]
                if series_key in data[series_field]:
                    values = data[series_field][series_key]
                    if len(classes) == len(values):
                        # Convertir les classes en chaînes avec suffixe optionnel
                        class_labels = [f"{cls}{class_suffix}" for cls in classes]
                        return pd.DataFrame(
                            {class_label: class_labels, value_label: values}
                        )
            # Rechercher directement une clé correspondant à la série spécifiée
            elif (
                series_key and series_key in data and isinstance(data[series_key], list)
            ):
                classes = data[class_field]
                values = data[series_key]
                if len(classes) == len(values):
                    # Convertir les classes en chaînes avec suffixe optionnel
                    class_labels = [f"{cls}{class_suffix}" for cls in classes]
                    return pd.DataFrame(
                        {class_label: class_labels, value_label: values}
                    )

    # Transformation spécifique pour l'extraction de données d'élévation
    elif transform_type == "elevation_distribution":
        if isinstance(data, dict) and "elevation" in data:
            elevation_data = data["elevation"]
            if (
                isinstance(elevation_data, dict)
                and "classes" in elevation_data
                and "subset" in elevation_data
            ):
                classes = elevation_data["classes"]
                subset = elevation_data["subset"]

                if len(classes) == len(subset):
                    return pd.DataFrame({"class_name": classes, "values": subset})

    # Transformation générique pour données avec subset/complement en format empilé
    elif transform_type == "subset_complement_stacked":
        data_field = params.get("data_field", None)
        classes_field = params.get("classes_field", "classes")
        subset_field = params.get("subset_field", "subset")
        complement_field = params.get("complement_field", "complement")
        class_label = params.get("class_label", "class")
        subset_label = params.get("subset_label", "Subset")
        complement_label = params.get("complement_label", "Complement")
        value_field = params.get("value_field", "value")
        type_field = params.get("type_field", "type")
        class_suffix = params.get(
            "class_suffix", ""
        )  # Pour ajouter "m" aux altitudes par exemple

        # Extraire les données du bon niveau
        if data_field and isinstance(data, dict) and data_field in data:
            data = data[data_field]

        if (
            isinstance(data, dict)
            and classes_field in data
            and subset_field in data
            and complement_field in data
        ):
            classes = data[classes_field]
            subset = data[subset_field]
            complement = data[complement_field]

            if len(classes) == len(subset) == len(complement):
                # Créer un DataFrame en format long pour barres empilées
                rows = []
                for i, cls in enumerate(classes):
                    # Ajouter la ligne pour le subset
                    rows.append(
                        {
                            class_label: f"{cls}{class_suffix}",
                            type_field: subset_label,
                            value_field: subset[i],
                        }
                    )
                    # Ajouter la ligne pour le complement
                    rows.append(
                        {
                            class_label: f"{cls}{class_suffix}",
                            type_field: complement_label,
                            value_field: complement[i],
                        }
                    )

                return pd.DataFrame(rows)

    # Transformation pour aires empilées normalisées (stacked area à 100%)
    elif transform_type == "stacked_area_normalized":
        x_field = params.get("x_field", "x")
        y_fields = params.get("y_fields", [])  # Liste des séries à empiler

        if (
            isinstance(data, dict)
            and x_field in data
            and all(field in data for field in y_fields)
        ):
            x_values = data[x_field]

            # Créer un DataFrame avec x et toutes les séries
            df_data = {x_field: x_values}
            for field in y_fields:
                df_data[field] = data[field]

            df = pd.DataFrame(df_data)

            # Calculer le total pour chaque point x pour la normalisation
            df["total"] = df[y_fields].sum(axis=1)

            # Convertir en pourcentages (0-100%)
            for field in y_fields:
                df[field] = (df[field] / df["total"] * 100).fillna(0)

            # Supprimer la colonne total
            df = df.drop("total", axis=1)

            return df

    # Transformation pour une série simple en DataFrame (pour area chart)
    elif transform_type == "simple_series_to_df":
        x_field = params.get("x_field", "x")
        y_field = params.get("y_field", "y")
        series_name = params.get(
            "series_name", "series"
        )  # Nom de la série pour la légende

        if isinstance(data, dict) and x_field in data and y_field in data:
            x_values = data[x_field]
            y_values = data[y_field]

            if len(x_values) == len(y_values):
                # Convertir les valeurs en pourcentages si nécessaire
                if params.get("convert_to_percentage", False):
                    y_values = [v * 100 for v in y_values]

                return pd.DataFrame({x_field: x_values, series_name: y_values})

    # Transformation pour graphique pyramide (valeurs négatives/positives)
    elif transform_type == "pyramid_chart":
        class_field = params.get("class_field", "class_name")
        series_field = params.get("series_field", "series")
        left_series = params.get(
            "left_series"
        )  # Série pour le côté gauche (valeurs négatives)
        right_series = params.get(
            "right_series"
        )  # Série pour le côté droit (valeurs positives)
        left_label = params.get("left_label", "Left")
        right_label = params.get("right_label", "Right")
        class_suffix = params.get("class_suffix", "")
        value_field = params.get("value_field", "value")
        type_field = params.get("type_field", "type")
        class_label = params.get("class_label", "class")

        if isinstance(data, dict) and class_field in data and series_field in data:
            classes = data[class_field]
            series_data = data[series_field]

            if (
                isinstance(series_data, dict)
                and left_series in series_data
                and right_series in series_data
            ):
                left_values = series_data[left_series]
                right_values = series_data[right_series]

                if len(classes) == len(left_values) == len(right_values):
                    rows = []
                    for i, cls in enumerate(classes):
                        # Côté gauche avec valeurs négatives
                        rows.append(
                            {
                                class_label: f"{cls}{class_suffix}",
                                type_field: left_label,
                                value_field: -abs(
                                    left_values[i]
                                ),  # Négatif pour le côté gauche
                            }
                        )
                        # Côté droit avec valeurs positives
                        rows.append(
                            {
                                class_label: f"{cls}{class_suffix}",
                                type_field: right_label,
                                value_field: abs(
                                    right_values[i]
                                ),  # Positif pour le côté droit
                            }
                        )

                    return pd.DataFrame(rows)

    # Transformation for histograms (bins/counts)
    elif transform_type == "bins_to_df":
        bin_field = params.get("bin_field", "bins")
        count_field = params.get("count_field", "counts")
        x_field = params.get("x_field", "bin")
        y_field = params.get("y_field", "count")
        use_percentages = params.get("use_percentages", False)
        percentage_field = params.get("percentage_field", "percentages")

        if isinstance(data, dict) and bin_field in data and count_field in data:
            # Get the data
            bins = data[bin_field]
            counts = data[count_field]

            # Use percentages if available and requested
            if use_percentages and percentage_field in data:
                values = data[percentage_field]
            else:
                values = counts

            # Make sure lengths match - typically we have one more bin than count
            if len(bins) == len(values) + 1:
                bins = bins[:-1]  # Remove the last bin

            if len(bins) == len(values):
                # Create bin labels for better display
                bin_labels = []
                for i in range(len(bins)):
                    if i < len(bins) - 1:
                        # Create range labels like "10-20"
                        next_bin = (
                            bins[i + 1]
                            if i + 1 < len(bins)
                            else bins[i] + (bins[i] - bins[i - 1] if i > 0 else 10)
                        )
                        bin_labels.append(f"{bins[i]}-{next_bin}")
                    else:
                        # Last bin - handle as "X+"
                        bin_labels.append(f"{bins[i]}+")

                # Create a DataFrame with the correct column names
                return pd.DataFrame(
                    {
                        x_field: bin_labels,
                        y_field: values,
                        "bin_value": bins,  # Keep original bin values for sorting
                    }
                )

    # Transformation pour données mensuelles/phénologiques
    elif transform_type == "monthly_data":
        labels_field = params.get("labels_field", "labels")
        data_field = params.get("data_field", "month_data")
        series_name = params.get("series_name")  # Si spécifié, n'extrait qu'une série
        melt = params.get("melt", False)  # Si True, transforme en format long

        if isinstance(data, dict) and labels_field in data and data_field in data:
            labels = data[labels_field]
            month_data = data[data_field]

            if isinstance(month_data, dict):
                if series_name and series_name in month_data:
                    # Une seule série
                    return pd.DataFrame(
                        {"labels": labels, series_name: month_data[series_name]}
                    )
                else:
                    # Toutes les séries
                    df = pd.DataFrame({"labels": labels})
                    for series, values in month_data.items():
                        if len(values) == len(labels):
                            df[series] = values

                    # Convertir en format long si demandé
                    if melt and len(df.columns) > 1:
                        return pd.melt(
                            df,
                            id_vars=["labels"],
                            var_name="series",
                            value_name="value",
                        )
                    return df

    # Transformation pour les données de distribution Holdridge avec categories/labels
    elif transform_type == "category_with_labels":
        category_field = params.get("category_field", "categories")
        count_field = params.get("count_field", "counts")
        label_field = params.get("label_field", "labels")
        percentage_field = params.get("percentage_field", "percentages")
        use_percentages = params.get("use_percentages", True)
        x_field = params.get("x_field", "category_label")
        y_field = params.get("y_field", "value")

        if isinstance(data, dict) and category_field in data and label_field in data:
            result = []
            categories = data[category_field]
            labels = data[label_field]

            if len(categories) == len(labels):
                # Utiliser les pourcentages si disponibles et demandés
                if use_percentages and percentage_field in data:
                    values = data[percentage_field]
                elif count_field in data:
                    values = data[count_field]
                else:
                    return data

                if len(values) == len(categories):
                    for i in range(len(categories)):
                        result.append(
                            {
                                x_field: labels[i],
                                y_field: values[i],
                                "category": categories[i],
                            }
                        )

                    return pd.DataFrame(result)

    # No transformation or unrecognized type
    return data
