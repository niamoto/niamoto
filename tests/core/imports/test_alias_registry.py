"""Tests for the column alias registry."""

import pytest

from niamoto.core.imports.ml.alias_registry import AliasRegistry, _normalize


class TestNormalize:
    """Test header normalization."""

    def test_lowercase(self):
        assert _normalize("DBH") == "dbh"

    def test_accents_removed(self):
        assert _normalize("diamètre") == "diametre"
        assert _normalize("espèce") == "espece"
        assert _normalize("höhe") == "hohe"

    def test_separators_to_underscore(self):
        assert _normalize("tree-height") == "tree_height"
        assert _normalize("tree height") == "tree_height"
        assert _normalize("tree.height") == "tree_height"

    def test_special_chars_stripped(self):
        assert _normalize("dbh (cm)") == "dbh_cm"
        assert _normalize("height[m]") == "heightm"

    def test_empty_string(self):
        assert _normalize("") == ""

    def test_unicode_transliteration(self):
        assert _normalize("café") == "cafe"
        assert _normalize("naïve") == "naive"
        assert _normalize("señor") == "senor"


class TestAliasRegistry:
    """Test the alias registry loading and matching."""

    @pytest.fixture
    def registry(self):
        return AliasRegistry()

    def test_loads_default_yaml(self, registry):
        assert len(registry.concepts) > 20

    def test_exact_match_english(self, registry):
        concept, score = registry.match("dbh")
        assert concept == "measurement.diameter"
        assert score == 1.0

    def test_exact_match_french(self, registry):
        concept, score = registry.match("hauteur")
        assert concept == "measurement.height"
        assert score == 1.0

    def test_exact_match_spanish(self, registry):
        concept, score = registry.match("latitud")
        assert concept == "location.latitude"
        assert score == 1.0

    def test_exact_match_dwc(self, registry):
        concept, score = registry.match("decimalLatitude")
        assert concept == "location.latitude"
        assert score == 1.0

    def test_exact_match_case_insensitive(self, registry):
        concept, score = registry.match("ScientificName")
        assert concept == "taxonomy.species"
        assert score == 1.0

    def test_accent_normalization(self, registry):
        concept, score = registry.match("diamètre")
        assert concept == "measurement.diameter"
        assert score == 1.0

    def test_fuzzy_match_typo(self, registry):
        concept, score = registry.match("diametr")
        assert concept == "measurement.diameter"
        assert score >= 0.8

    def test_no_match_random(self, registry):
        concept, score = registry.match("foobar_xyz")
        assert concept is None
        assert score == 0.0

    def test_no_match_anonymous(self, registry):
        concept, score = registry.match("X1")
        assert concept is None or score < 0.8

    def test_match_top_k(self, registry):
        results = registry.match_top_k("lat", k=3)
        assert len(results) <= 3
        # latitude should be among top results
        concepts = [c for c, _ in results]
        assert "location.latitude" in concepts

    def test_match_top_k_empty(self, registry):
        results = registry.match_top_k("", k=3)
        assert results == []

    def test_concepts_list(self, registry):
        concepts = registry.concepts
        assert "taxonomy.species" in concepts
        assert "location.latitude" in concepts
        assert "measurement.diameter" in concepts
        assert "event.date" in concepts

    def test_custom_yaml_path(self, tmp_path):
        """Test loading a custom alias file."""
        custom = tmp_path / "aliases.yaml"
        custom.write_text("test.concept:\n  en: [test_col, my_test]\n")
        reg = AliasRegistry(alias_path=custom)
        concept, score = reg.match("test_col")
        assert concept == "test.concept"
        assert score == 1.0

    def test_separator_handling(self, registry):
        """Column names with different separators should match."""
        concept, score = registry.match("tree_height")
        assert concept == "measurement.height"
        assert score == 1.0

    def test_german_match(self, registry):
        concept, score = registry.match("breitengrad")
        assert concept == "location.latitude"
        assert score == 1.0

    def test_indonesian_match(self, registry):
        concept, score = registry.match("spesies")
        assert concept == "taxonomy.species"
        assert score == 1.0
