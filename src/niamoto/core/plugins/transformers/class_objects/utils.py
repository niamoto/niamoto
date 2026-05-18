"""Shared helpers for class-object transformers."""

from typing import Iterable

import pandas as pd

from niamoto.common.exceptions import DataTransformError


def aggregate_class_values(
    data: pd.DataFrame,
    group_columns: Iterable[str],
) -> pd.DataFrame:
    """Return class-object rows with duplicate numeric values summed."""
    group_columns = list(group_columns)
    aggregated = data.copy()
    try:
        aggregated["class_value"] = pd.to_numeric(
            aggregated["class_value"], errors="raise"
        )
    except (TypeError, ValueError) as exc:
        raise DataTransformError(
            "Failed to convert class_value to numeric values",
            details={"error": str(exc)},
        ) from exc

    return (
        aggregated.groupby(group_columns, as_index=False, dropna=False)["class_value"]
        .sum()
        .reset_index(drop=True)
    )
