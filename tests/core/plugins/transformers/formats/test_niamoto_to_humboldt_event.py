"""Tests for the Niamoto to Humboldt/Event transformer."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from niamoto.common.exceptions import DataTransformError
from niamoto.core.plugins.transformers.formats.niamoto_to_humboldt_event import (
    NiamotoHumboldtEventTransformer,
)


def test_humboldt_event_transformer_maps_source_fields_and_generators():
    transformer = NiamotoHumboldtEventTransformer(Mock())

    result = transformer.transform(
        {"plot_id": "plot-1", "plot_name": "Mont Panié"},
        {
            "mapping": {
                "eventID": {"source": "plot_id"},
                "locationID": "plot_name",
                "basisOfRecord": {
                    "generator": "constant",
                    "params": {"value": "HumanObservation"},
                },
            }
        },
    )

    assert result == {
        "eventID": "plot-1",
        "locationID": "Mont Panié",
        "basisOfRecord": "HumanObservation",
    }


def test_humboldt_event_transformer_rejects_invalid_mapping_shape():
    transformer = NiamotoHumboldtEventTransformer(Mock())

    with pytest.raises(
        DataTransformError, match="Humboldt/Event transformation failed"
    ):
        transformer.transform(
            {"plot_id": "plot-1"},
            {"mapping": {"eventID": ["not", "valid"]}},
        )
