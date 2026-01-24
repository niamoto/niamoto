# src/niamoto/common/i18n.py
"""
Internationalization support for Niamoto user content.

This module provides utilities for handling localized strings in configuration
files, allowing users to specify content in multiple languages.

Supports two formats:
- Simple string (uses default language): "Distribution des espèces"
- Localized dict: {"fr": "Distribution des espèces", "en": "Species distribution"}
"""

from typing import Any, Dict, List, Optional, Union

# Type alias for localized strings
LocalizedString = Union[str, Dict[str, str]]


class I18nResolver:
    """
    Resolver for internationalized content.

    Detects the format (simple string or localized dict) and resolves
    the value for a given language with intelligent fallback.

    Example usage:
        resolver = I18nResolver(default_lang="fr")

        # Simple string - returns as-is
        resolver.resolve("Distribution", "en")  # -> "Distribution"

        # Localized dict - returns appropriate translation
        resolver.resolve({"fr": "Distribution", "en": "Distribution"}, "en")  # -> "Distribution"

        # Fallback to default language if translation missing
        resolver.resolve({"fr": "Distribution"}, "en")  # -> "Distribution"
    """

    # Default supported languages (can be overridden in site config)
    DEFAULT_LANGUAGES = ["fr", "en"]

    def __init__(
        self,
        default_lang: str = "fr",
        available_languages: Optional[List[str]] = None,
    ):
        """
        Initialize the resolver.

        Args:
            default_lang: Default language code (used for simple strings and fallback)
            available_languages: List of language codes to support
        """
        self.default_lang = default_lang
        self.available_languages = available_languages or self.DEFAULT_LANGUAGES

        # Ensure default language is in available languages
        if self.default_lang not in self.available_languages:
            self.available_languages.insert(0, self.default_lang)

    def resolve(
        self,
        value: Any,
        lang: Optional[str] = None,
        fallback: Optional[str] = None,
    ) -> Optional[str]:
        """
        Resolve a potentially localized value to a string for the given language.

        Args:
            value: The value to resolve (string, dict, or None)
            lang: Target language code. If None, uses default_lang.
            fallback: Fallback value if resolution fails

        Returns:
            Resolved string value, or fallback if resolution fails
        """
        if value is None:
            return fallback

        target_lang = lang or self.default_lang

        # Simple string - return as-is
        if isinstance(value, str):
            return value

        # Localized dict
        if isinstance(value, dict):
            # Try exact language match
            if target_lang in value:
                return value[target_lang]

            # Try default language
            if self.default_lang in value and self.default_lang != target_lang:
                return value[self.default_lang]

            # Try first available translation
            for available_lang in self.available_languages:
                if available_lang in value:
                    return value[available_lang]

            # Return first available value as last resort
            if value:
                return next(iter(value.values()))

            return fallback

        # Unknown type - convert to string
        return str(value) if value is not None else fallback

    def resolve_dict(
        self,
        data: Dict[str, Any],
        lang: Optional[str] = None,
        keys: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Resolve all localizable fields in a dictionary.

        Args:
            data: Dictionary containing potentially localized values
            lang: Target language code
            keys: Specific keys to resolve. If None, resolves all LocalizedString-like values.

        Returns:
            New dictionary with resolved string values
        """
        if not data:
            return {}

        result = dict(data)
        target_lang = lang or self.default_lang

        if keys:
            # Resolve only specified keys
            for key in keys:
                if key in result:
                    result[key] = self.resolve(result[key], target_lang)
        else:
            # Resolve all dict-type values that look like localized strings
            for key, value in data.items():
                if self._is_localized_dict(value):
                    result[key] = self.resolve(value, target_lang)

        return result

    def resolve_recursive(
        self,
        data: Any,
        lang: Optional[str] = None,
    ) -> Any:
        """
        Recursively resolve all localized strings in a nested structure.

        Traverses dictionaries and lists, resolving any localized dict values.

        Args:
            data: Data structure to process (dict, list, or scalar)
            lang: Target language code

        Returns:
            Data structure with all localized strings resolved
        """
        target_lang = lang or self.default_lang

        if isinstance(data, dict):
            # Check if this dict is a localized string
            if self._is_localized_dict(data):
                return self.resolve(data, target_lang)

            # Otherwise recurse into children
            return {
                key: self.resolve_recursive(value, target_lang)
                for key, value in data.items()
            }

        if isinstance(data, list):
            return [self.resolve_recursive(item, target_lang) for item in data]

        # Scalar value - return as-is
        return data

    def _is_localized_dict(self, value: Any) -> bool:
        """
        Check if a value appears to be a localized string dict.

        A localized dict should:
        - Be a dict
        - Have only string values
        - Have at least one key that looks like a language code

        Args:
            value: Value to check

        Returns:
            True if value appears to be a localized dict
        """
        if not isinstance(value, dict):
            return False

        if not value:
            return False

        # Check if all values are strings
        if not all(isinstance(v, str) for v in value.values()):
            return False

        # Check if at least one key is a known language code
        known_lang_codes = {"fr", "en", "es", "de", "it", "pt", "nl", "ja", "zh", "ko"}
        return any(key in known_lang_codes for key in value.keys())

    def extract_languages(self, data: Any) -> List[str]:
        """
        Extract all language codes found in a data structure.

        Useful for auto-detecting which languages are configured.

        Args:
            data: Data structure to scan

        Returns:
            List of unique language codes found
        """
        languages = set()
        self._collect_languages(data, languages)
        return sorted(languages)

    def _collect_languages(self, data: Any, languages: set) -> None:
        """Recursively collect language codes from data structure."""
        if isinstance(data, dict):
            if self._is_localized_dict(data):
                languages.update(data.keys())
            else:
                for value in data.values():
                    self._collect_languages(value, languages)
        elif isinstance(data, list):
            for item in data:
                self._collect_languages(item, languages)

    def has_translations(self, value: Any) -> bool:
        """
        Check if a value has translations (is a localized dict).

        Args:
            value: Value to check

        Returns:
            True if the value is a dict with language keys
        """
        return self._is_localized_dict(value)

    def get_all_translations(self, value: LocalizedString) -> Dict[str, str]:
        """
        Get all translations for a localized value.

        Args:
            value: Localized string (dict or simple string)

        Returns:
            Dict of {lang_code: translation}. For simple strings,
            returns {default_lang: value}.
        """
        if isinstance(value, str):
            return {self.default_lang: value}
        if isinstance(value, dict):
            return {k: v for k, v in value.items() if isinstance(v, str)}
        return {}

    def make_localized(
        self,
        value: str,
        translations: Optional[Dict[str, str]] = None,
    ) -> LocalizedString:
        """
        Create a localized string from a base value and optional translations.

        Args:
            value: Base value (assigned to default language)
            translations: Dict of {lang_code: translation} for other languages

        Returns:
            LocalizedString (dict if multiple languages, string if single)
        """
        if not translations:
            return value

        result = {self.default_lang: value}
        result.update(translations)

        # If only one language and it's the default, return as simple string
        if len(result) == 1 and self.default_lang in result:
            return value

        return result


# Convenience function for one-off resolution
def resolve_localized(
    value: Any,
    lang: str = "fr",
    default_lang: str = "fr",
    fallback: Optional[str] = None,
) -> Optional[str]:
    """
    Convenience function to resolve a localized value without creating a resolver.

    Args:
        value: Value to resolve
        lang: Target language
        default_lang: Fallback language
        fallback: Value to return if resolution fails

    Returns:
        Resolved string
    """
    resolver = I18nResolver(default_lang=default_lang)
    return resolver.resolve(value, lang, fallback)
