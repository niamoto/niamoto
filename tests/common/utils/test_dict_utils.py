"""Tests for dict_utils module."""

import logging
from niamoto.common.utils.dict_utils import get_nested_value


class TestGetNestedValue:
    """Test get_nested_value function."""

    def test_get_simple_key(self):
        """Test getting a simple key from dictionary."""
        data = {"key": "value"}
        result = get_nested_value(data, "key")
        assert result == "value"

    def test_get_nested_key(self):
        """Test getting a nested key from dictionary."""
        data = {"level1": {"level2": {"level3": "value"}}}
        result = get_nested_value(data, "level1.level2.level3")
        assert result == "value"

    def test_get_missing_key_returns_default(self):
        """Test that missing key returns default value."""
        data = {"key": "value"}
        result = get_nested_value(data, "missing", default="default")
        assert result == "default"

    def test_get_missing_nested_key_returns_default(self):
        """Test that missing nested key returns default value."""
        data = {"level1": {"level2": "value"}}
        result = get_nested_value(data, "level1.missing", default="default")
        assert result == "default"

    def test_get_none_value_returns_default(self):
        """Test that None value returns default."""
        data = {"key": None}
        result = get_nested_value(data, "key", default="default")
        assert result == "default"

    def test_non_dict_data_returns_default_and_warns(self, caplog):
        """Test that non-dict data returns default and logs warning."""
        with caplog.at_level(logging.WARNING):
            result = get_nested_value("not_a_dict", "key", default="default")

        assert result == "default"
        assert "Cannot access key path" in caplog.text
        assert "on non-dict data" in caplog.text

    def test_non_dict_in_path_returns_default_and_warns(self, caplog):
        """Test that encountering non-dict in path returns default and warns."""
        data = {"level1": "not_a_dict"}

        with caplog.at_level(logging.WARNING):
            result = get_nested_value(data, "level1.level2", default="default")

        assert result == "default"
        assert "Cannot access key" in caplog.text
        assert "on non-dict element in path" in caplog.text

    def test_empty_dict(self):
        """Test with empty dictionary."""
        data = {}
        result = get_nested_value(data, "key", default="default")
        assert result == "default"

    def test_deeply_nested_structure(self):
        """Test with deeply nested structure."""
        data = {"a": {"b": {"c": {"d": {"e": "deep_value"}}}}}
        result = get_nested_value(data, "a.b.c.d.e")
        assert result == "deep_value"
