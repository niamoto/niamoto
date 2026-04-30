"""Transformer plugin for Humboldt/Event-oriented standard records."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import Field

from niamoto.common.exceptions import DataTransformError
from niamoto.core.plugins.base import PluginType, TransformerPlugin, register
from niamoto.core.plugins.models import BasePluginParams, PluginConfig


class HumboldtEventTransformerParams(BasePluginParams):
    """Parameters for mapping source rows to Humboldt/Event terms."""

    mapping: dict[str, Any] = Field(
        ...,
        description="Mapping of Humboldt/Event terms to source fields or generators",
    )


class NiamotoHumboldtEventConfig(PluginConfig):
    """Configuration for the Humboldt/Event transformer plugin."""

    plugin: Literal["niamoto_to_humboldt_event"] = "niamoto_to_humboldt_event"
    params: HumboldtEventTransformerParams  # type: ignore[assignment]


@register("niamoto_to_humboldt_event", PluginType.TRANSFORMER)
class NiamotoHumboldtEventTransformer(TransformerPlugin):
    """Transform one Niamoto event or inventory row to Humboldt/Event terms."""

    config_model = NiamotoHumboldtEventConfig
    param_schema = HumboldtEventTransformerParams

    def validate_config(self, config: Any) -> NiamotoHumboldtEventConfig:
        """Validate raw transformer configuration."""
        try:
            if hasattr(config, "model_dump"):
                dumped = config.model_dump()
                if "mapping" in dumped:
                    config = {
                        "plugin": "niamoto_to_humboldt_event",
                        "params": config,
                    }
            if (
                isinstance(config, dict)
                and "params" not in config
                and "mapping" in config
            ):
                config = {
                    "plugin": "niamoto_to_humboldt_event",
                    "params": config,
                }
            validated = self.config_model.model_validate(config)
            _validate_mapping_shape(validated.params.mapping)
            return validated
        except Exception as exc:
            raise ValueError(f"Invalid configuration: {str(exc)}") from exc

    def transform(self, data: dict[str, Any], config: Any) -> dict[str, Any]:
        """Map a single source row to Humboldt/Event terms."""
        try:
            validated = self.validate_config(config)
            return {
                term: _resolve_mapping_value(data, mapping)
                for term, mapping in validated.params.mapping.items()
            }
        except Exception as exc:
            raise DataTransformError(
                f"Humboldt/Event transformation failed: {str(exc)}"
            ) from exc


def _validate_mapping_shape(mapping: dict[str, Any]) -> None:
    for term, value in mapping.items():
        if isinstance(value, str):
            continue
        if isinstance(value, dict):
            has_source = bool(value.get("source"))
            has_generator = bool(value.get("generator"))
            if has_source != has_generator:
                continue
        raise ValueError(
            f"Mapping for '{term}' must be a source string or an object "
            "with exactly one of source or generator."
        )


def _resolve_mapping_value(record: dict[str, Any], mapping: Any) -> Any:
    if isinstance(mapping, str):
        return _read_path(record, _normalize_source_path(mapping))

    if not isinstance(mapping, dict):
        raise ValueError(f"Unsupported mapping shape: {mapping!r}")

    if mapping.get("source"):
        return _read_path(record, _normalize_source_path(str(mapping["source"])))

    if mapping.get("generator"):
        return _generate_value(str(mapping["generator"]), mapping.get("params") or {})

    raise ValueError(f"Unsupported mapping shape: {mapping!r}")


def _normalize_source_path(source: str) -> str:
    if source.startswith("@source."):
        return source.removeprefix("@source.")
    if source.startswith("@"):
        path = source.removeprefix("@")
        if "." in path:
            return path.split(".", 1)[1]
        return path
    return source


def _read_path(record: dict[str, Any], path: str) -> Any:
    value: Any = record
    for part in path.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def _generate_value(generator: str, params: dict[str, Any]) -> Any:
    if generator == "constant":
        return params.get("value")
    if generator == "current_date":
        return date.today().isoformat()
    raise ValueError(f"Unknown generator '{generator}'")
