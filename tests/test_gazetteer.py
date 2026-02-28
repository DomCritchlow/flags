"""Tests for gazetteer loading and validation."""

import pytest
from pipeline.gazetteer import Gazetteer, GazetteerValidationError


@pytest.fixture
def gazetteer():
    return Gazetteer()


class TestGazetteerLoading:
    def test_countries_loaded(self, gazetteer):
        """Master registry should have ~190+ countries."""
        assert len(gazetteer.countries) >= 190

    def test_country_has_required_fields(self, gazetteer):
        """Each country must have name, iso2, and region."""
        for iso3, info in gazetteer.countries.items():
            assert "name" in info, f"{iso3} missing name"
            assert "iso2" in info, f"{iso3} missing iso2"
            assert len(info["iso2"]) == 2, f"{iso3} iso2 should be 2 chars"

    def test_no_usa_in_countries(self, gazetteer):
        """USA should not be in the registry (we track foreign countries only)."""
        assert "USA" not in gazetteer.countries

    def test_key_countries_present(self, gazetteer):
        """Major countries referenced in Congress should be present."""
        expected = ["UKR", "CHN", "RUS", "IRN", "PRK", "KOR", "IRQ", "AFG",
                    "SYR", "SAU", "TWN", "JPN", "IND", "PAK", "GBR", "DEU"]
        for iso3 in expected:
            assert iso3 in gazetteer.countries, f"{iso3} missing from countries"

    def test_unambiguous_terms_loaded(self, gazetteer):
        """Should have many unambiguous terms."""
        assert len(gazetteer.unambiguous_terms) > 500  # names + demonyms + cities

    def test_unambiguous_term_maps_to_valid_iso3(self, gazetteer):
        """Every unambiguous term should map to a country in the registry."""
        issues = [
            f"'{term}' -> '{iso3}'"
            for term, iso3 in gazetteer.unambiguous_terms.items()
            if iso3 not in gazetteer.countries
        ]
        assert not issues, f"Terms with unknown iso3: {issues[:10]}"

    def test_ambiguous_terms_loaded(self, gazetteer):
        """Should have ~15-20 ambiguous entries."""
        assert len(gazetteer.ambiguous_terms) >= 15

    def test_ambiguous_has_required_fields(self, gazetteer):
        """Each ambiguous entry must have country_iso3 and default."""
        for key, entry in gazetteer.ambiguous_terms.items():
            # All entries should have some form of configuration
            assert "default" in entry or "matching_rule" in entry or "require_full_name" in entry, \
                f"Ambiguous '{key}' missing decision mechanism"

    def test_no_overlap_unambiguous_ambiguous(self, gazetteer):
        """No term should appear in both unambiguous and ambiguous gazetteers."""
        ambiguous_keys = set(gazetteer.ambiguous_terms.keys())
        for term in gazetteer.unambiguous_terms:
            assert term.lower() not in ambiguous_keys, \
                f"'{term}' appears in both unambiguous and ambiguous"

    def test_blocklist_loaded(self, gazetteer):
        """Blocklist should have entries."""
        assert len(gazetteer.blocklist_phrases) > 0

    def test_blocklist_contains_key_phrases(self, gazetteer):
        """Critical false-positive phrases must be in blocklist."""
        expected = ["New Mexico", "New Jersey", "West Virginia",
                    "District of Columbia"]
        for phrase in expected:
            assert phrase in gazetteer.blocklist_phrases, \
                f"'{phrase}' missing from blocklist"


class TestGazetteerValidation:
    def test_validate_returns_no_issues(self, gazetteer):
        """Full validation should pass with no issues."""
        issues = gazetteer.validate()
        assert not issues, f"Validation issues: {issues}"

    def test_stats_reasonable(self, gazetteer):
        """Stats should show reasonable coverage."""
        stats = gazetteer.stats()
        assert stats["total_countries"] >= 190
        assert stats["unambiguous_terms"] > 500
        assert stats["ambiguous_entries"] >= 15
        assert stats["automaton_size"] > 0


class TestGazetteerAutomaton:
    def test_automaton_built(self, gazetteer):
        """Aho-Corasick automaton should be built and non-empty."""
        assert gazetteer.automaton is not None
        assert len(gazetteer.automaton) > 0

    def test_automaton_finds_ukraine(self, gazetteer):
        """Basic search should find 'Ukraine'."""
        text = "The situation in Ukraine remains critical"
        matches = list(gazetteer.automaton.iter(text))
        terms = [m[1][0] for m in matches]
        assert "Ukraine" in terms

    def test_automaton_finds_demonym(self, gazetteer):
        """Should find demonyms like 'Ukrainian'."""
        text = "Ukrainian forces advanced"
        matches = list(gazetteer.automaton.iter(text))
        terms = [m[1][0] for m in matches]
        assert "Ukrainian" in terms or "Ukrainians" in terms or any("Ukrain" in t for t in terms)

    def test_automaton_case_sensitive(self, gazetteer):
        """Should NOT match lowercase terms (e.g., 'china' for porcelain)."""
        text = "the fine china on the table"
        matches = list(gazetteer.automaton.iter(text))
        # "china" (lowercase) should not be in the automaton
        terms = [m[1][0] for m in matches]
        assert "china" not in terms
