"""Test module for the I18nResolver class."""

import unittest
from niamoto.common.i18n import I18nResolver, LocalizedString, resolve_localized


class TestI18nResolver(unittest.TestCase):
    """Test cases for I18nResolver functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.resolver = I18nResolver(default_lang="fr")

    def test_resolve_simple_string(self):
        """Test resolving a simple string returns it unchanged."""
        result = self.resolver.resolve("Distribution des espèces", "en")
        self.assertEqual(result, "Distribution des espèces")

    def test_resolve_simple_string_any_language(self):
        """Test that simple strings are returned for any language."""
        value = "Same for all"
        self.assertEqual(self.resolver.resolve(value, "fr"), "Same for all")
        self.assertEqual(self.resolver.resolve(value, "en"), "Same for all")
        self.assertEqual(self.resolver.resolve(value, "de"), "Same for all")

    def test_resolve_localized_dict_exact_match(self):
        """Test resolving a localized dict with exact language match."""
        value = {"fr": "Distribution", "en": "Distribution"}
        self.assertEqual(self.resolver.resolve(value, "en"), "Distribution")
        self.assertEqual(self.resolver.resolve(value, "fr"), "Distribution")

    def test_resolve_localized_dict_fallback_to_default(self):
        """Test fallback to default language when translation is missing."""
        value = {"fr": "Distribution"}
        result = self.resolver.resolve(value, "en")
        self.assertEqual(result, "Distribution")  # Falls back to fr (default)

    def test_resolve_localized_dict_fallback_to_first_available(self):
        """Test fallback to first available when default is also missing."""
        resolver = I18nResolver(default_lang="de")  # German default, not in dict
        value = {"fr": "Distribution", "en": "Distribution"}
        result = resolver.resolve(value, "es")
        # Should fall back to first available in available_languages order
        self.assertIn(result, ["Distribution", "Distribution"])

    def test_resolve_none_returns_fallback(self):
        """Test that None value returns the fallback."""
        result = self.resolver.resolve(None, "fr", fallback="Default")
        self.assertEqual(result, "Default")

    def test_resolve_none_returns_none_without_fallback(self):
        """Test that None value returns None when no fallback provided."""
        result = self.resolver.resolve(None, "fr")
        self.assertIsNone(result)

    def test_resolve_empty_dict_returns_fallback(self):
        """Test that empty dict returns fallback."""
        result = self.resolver.resolve({}, "fr", fallback="Default")
        self.assertEqual(result, "Default")

    def test_resolve_uses_default_lang_when_lang_is_none(self):
        """Test that default language is used when lang param is None."""
        value = {"fr": "French", "en": "English"}
        result = self.resolver.resolve(value, None)
        self.assertEqual(result, "French")  # Default is fr

    def test_resolve_unknown_type_converts_to_string(self):
        """Test that unknown types are converted to string."""
        result = self.resolver.resolve(42, "fr")
        self.assertEqual(result, "42")

    def test_resolve_dict_specific_keys(self):
        """Test resolving specific keys in a dictionary."""
        data = {
            "title": {"fr": "Titre", "en": "Title"},
            "description": {"fr": "Description FR", "en": "Description EN"},
            "other": "unchanged",
        }
        result = self.resolver.resolve_dict(data, "en", keys=["title", "description"])
        self.assertEqual(result["title"], "Title")
        self.assertEqual(result["description"], "Description EN")
        self.assertEqual(result["other"], "unchanged")

    def test_resolve_dict_all_localized_fields(self):
        """Test resolving all localized fields in a dictionary."""
        data = {
            "title": {"fr": "Titre", "en": "Title"},
            "count": 42,  # Not a localized string
        }
        result = self.resolver.resolve_dict(data, "en")
        self.assertEqual(result["title"], "Title")
        self.assertEqual(result["count"], 42)

    def test_resolve_recursive_nested_structure(self):
        """Test recursive resolution of nested structures."""
        data = {
            "site": {
                "title": {"fr": "Atlas", "en": "Atlas"},
                "navigation": [
                    {"text": {"fr": "Accueil", "en": "Home"}, "url": "/"},
                    {"text": {"fr": "À propos", "en": "About"}, "url": "/about"},
                ],
            },
            "widgets": [
                {"title": {"fr": "Distribution", "en": "Distribution"}},
            ],
        }
        result = self.resolver.resolve_recursive(data, "en")

        self.assertEqual(result["site"]["title"], "Atlas")
        self.assertEqual(result["site"]["navigation"][0]["text"], "Home")
        self.assertEqual(result["site"]["navigation"][1]["text"], "About")
        self.assertEqual(result["widgets"][0]["title"], "Distribution")

    def test_resolve_recursive_preserves_non_localized(self):
        """Test that recursive resolution preserves non-localized values."""
        data = {
            "count": 42,
            "items": [1, 2, 3],
            "config": {"nested": {"value": 100}},
        }
        result = self.resolver.resolve_recursive(data, "en")
        self.assertEqual(result["count"], 42)
        self.assertEqual(result["items"], [1, 2, 3])
        self.assertEqual(result["config"]["nested"]["value"], 100)

    def test_is_localized_dict_valid(self):
        """Test detection of valid localized dicts."""
        self.assertTrue(self.resolver._is_localized_dict({"fr": "Test", "en": "Test"}))
        self.assertTrue(self.resolver._is_localized_dict({"fr": "Test"}))
        self.assertTrue(self.resolver._is_localized_dict({"en": "Test"}))

    def test_is_localized_dict_invalid(self):
        """Test detection rejects non-localized dicts."""
        # Not a dict
        self.assertFalse(self.resolver._is_localized_dict("string"))
        self.assertFalse(self.resolver._is_localized_dict(42))
        self.assertFalse(self.resolver._is_localized_dict(None))

        # Empty dict
        self.assertFalse(self.resolver._is_localized_dict({}))

        # Dict with non-string values
        self.assertFalse(self.resolver._is_localized_dict({"fr": 42}))
        self.assertFalse(self.resolver._is_localized_dict({"fr": {"nested": "dict"}}))

        # Dict with non-language keys
        self.assertFalse(
            self.resolver._is_localized_dict({"title": "value", "description": "desc"})
        )

    def test_extract_languages(self):
        """Test extracting language codes from a data structure."""
        data = {
            "title": {"fr": "Titre", "en": "Title"},
            "items": [
                {"name": {"fr": "Nom", "de": "Name"}},
            ],
        }
        languages = self.resolver.extract_languages(data)
        self.assertEqual(sorted(languages), ["de", "en", "fr"])

    def test_has_translations(self):
        """Test checking if a value has translations."""
        self.assertTrue(self.resolver.has_translations({"fr": "Test", "en": "Test"}))
        self.assertFalse(self.resolver.has_translations("Simple string"))
        self.assertFalse(self.resolver.has_translations(None))

    def test_get_all_translations_from_dict(self):
        """Test getting all translations from a localized dict."""
        value = {"fr": "Français", "en": "English"}
        result = self.resolver.get_all_translations(value)
        self.assertEqual(result, {"fr": "Français", "en": "English"})

    def test_get_all_translations_from_string(self):
        """Test getting translations from a simple string."""
        result = self.resolver.get_all_translations("Simple")
        self.assertEqual(result, {"fr": "Simple"})  # Default lang is fr

    def test_make_localized_with_translations(self):
        """Test creating a localized string with translations."""
        result = self.resolver.make_localized(
            "French value", translations={"en": "English value"}
        )
        self.assertEqual(result, {"fr": "French value", "en": "English value"})

    def test_make_localized_without_translations(self):
        """Test creating a localized string without translations returns simple string."""
        result = self.resolver.make_localized("Simple value")
        self.assertEqual(result, "Simple value")

    def test_default_lang_added_to_available_languages(self):
        """Test that default language is added to available languages if missing."""
        resolver = I18nResolver(default_lang="de", available_languages=["fr", "en"])
        self.assertIn("de", resolver.available_languages)
        self.assertEqual(resolver.available_languages[0], "de")

    def test_resolve_localized_convenience_function(self):
        """Test the convenience function for one-off resolution."""
        value = {"fr": "Français", "en": "English"}
        self.assertEqual(resolve_localized(value, lang="en"), "English")
        self.assertEqual(resolve_localized(value, lang="fr"), "Français")
        self.assertEqual(resolve_localized("Simple", lang="en"), "Simple")

    def test_real_world_config_example(self):
        """Test with a real-world configuration example."""
        config = {
            "site": {
                "title": {"fr": "Atlas de la Flore", "en": "Flora Atlas"},
                "lang": "fr",
            },
            "navigation": [
                {"text": {"fr": "Accueil", "en": "Home"}, "url": "/index.html"},
                {"text": {"fr": "Taxons", "en": "Taxa"}, "url": "/taxons/index.html"},
            ],
            "widgets": [
                {
                    "plugin": "bar_plot",
                    "title": {"fr": "Distribution", "en": "Distribution"},
                    "params": {
                        "labels": {
                            "x_axis": {"fr": "Nombre", "en": "Count"},
                        }
                    },
                }
            ],
        }

        # Resolve for French
        result_fr = self.resolver.resolve_recursive(config, "fr")
        self.assertEqual(result_fr["site"]["title"], "Atlas de la Flore")
        self.assertEqual(result_fr["navigation"][0]["text"], "Accueil")
        self.assertEqual(result_fr["widgets"][0]["title"], "Distribution")
        self.assertEqual(
            result_fr["widgets"][0]["params"]["labels"]["x_axis"], "Nombre"
        )

        # Resolve for English
        result_en = self.resolver.resolve_recursive(config, "en")
        self.assertEqual(result_en["site"]["title"], "Flora Atlas")
        self.assertEqual(result_en["navigation"][0]["text"], "Home")
        self.assertEqual(result_en["navigation"][1]["text"], "Taxa")
        self.assertEqual(result_en["widgets"][0]["params"]["labels"]["x_axis"], "Count")


class TestLocalizedStringType(unittest.TestCase):
    """Test the LocalizedString type alias compatibility."""

    def test_localized_string_accepts_str(self):
        """Test that LocalizedString accepts plain strings."""

        def accepts_localized(value: LocalizedString) -> str:
            if isinstance(value, str):
                return value
            return value.get("fr", "")

        self.assertEqual(accepts_localized("test"), "test")

    def test_localized_string_accepts_dict(self):
        """Test that LocalizedString accepts language dicts."""

        def accepts_localized(value: LocalizedString) -> str:
            if isinstance(value, str):
                return value
            return value.get("fr", "")

        self.assertEqual(accepts_localized({"fr": "test", "en": "test"}), "test")


if __name__ == "__main__":
    unittest.main()
