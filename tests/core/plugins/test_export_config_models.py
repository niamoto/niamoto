"""Tests for export.yml Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from niamoto.core.plugins.models import ExportConfig


def test_export_config_accepts_standard_profiles_alongside_exports():
    config = ExportConfig.model_validate(
        {
            "exports": [
                {
                    "name": "json_api",
                    "exporter": "json_api_exporter",
                    "params": {
                        "output_dir": "exports/api",
                        "detail_output_pattern": "{group}/{id}.json",
                    },
                    "groups": [],
                }
            ],
            "standard_profiles": [
                {
                    "name": "dwc_occurrences",
                    "standard": "darwin_core_occurrence",
                    "target_grain": "occurrence",
                    "source": {"type": "dataset", "name": "occurrences"},
                }
            ],
        }
    )

    assert config.exports[0].name == "json_api"
    assert config.standard_profiles[0].name == "dwc_occurrences"
    assert config.standard_profiles[0].validation_status == "draft"


def test_export_config_rejects_unsupported_standard_profile_type():
    with pytest.raises(ValidationError):
        ExportConfig.model_validate(
            {
                "exports": [],
                "standard_profiles": [
                    {
                        "name": "bad_profile",
                        "standard": "unknown_standard",
                        "target_grain": "occurrence",
                        "source": {"type": "dataset", "name": "occurrences"},
                    }
                ],
            }
        )
