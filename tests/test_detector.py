"""Tests for the country detection engine."""

import pytest
from pipeline.gazetteer import Gazetteer
from pipeline.detector import CountryDetector, Mention


@pytest.fixture
def gazetteer():
    return Gazetteer()


@pytest.fixture
def detector(gazetteer):
    return CountryDetector(gazetteer, enable_llm=False)


class TestTier1UnambiguousMatches:
    """Test Tier 1: Aho-Corasick dictionary matching."""

    def test_basic_country_name(self, detector):
        mentions = detector.detect(
            "The situation in Ukraine remains dire",
            "test-1", "bill"
        )
        iso3s = [m.iso3 for m in mentions]
        assert "UKR" in iso3s

    def test_multiple_countries(self, detector):
        mentions = detector.detect(
            "Relations between China and Japan deteriorated",
            "test-2", "hearing"
        )
        iso3s = [m.iso3 for m in mentions]
        assert "CHN" in iso3s
        assert "JPN" in iso3s

    def test_demonym_match(self, detector):
        mentions = detector.detect(
            "Iranian forces conducted exercises near the border",
            "test-3", "bill"
        )
        iso3s = [m.iso3 for m in mentions]
        assert "IRN" in iso3s

    def test_city_match(self, detector):
        mentions = detector.detect(
            "The bombing of Kabul caused international concern",
            "test-4", "hearing"
        )
        iso3s = [m.iso3 for m in mentions]
        assert "AFG" in iso3s

    def test_acronym_match(self, detector):
        mentions = detector.detect(
            "The DPRK launched another missile test",
            "test-5", "bill"
        )
        iso3s = [m.iso3 for m in mentions]
        assert "PRK" in iso3s

    def test_historical_name(self, detector):
        mentions = detector.detect(
            "The former state of Burma underwent democratic reforms",
            "test-6", "hearing"
        )
        iso3s = [m.iso3 for m in mentions]
        assert "MMR" in iso3s

    def test_longest_match_first(self, detector):
        """'South Korea' should match as one entity, not 'Korea' separately."""
        mentions = detector.detect(
            "South Korea announced new defense spending",
            "test-7", "bill"
        )
        iso3s = [m.iso3 for m in mentions]
        assert "KOR" in iso3s
        # Should NOT match North Korea
        assert "PRK" not in iso3s

    def test_dedup_per_record(self, detector):
        """Same country mentioned multiple times = one mention per record."""
        mentions = detector.detect(
            "Ukraine forces in Ukraine defended Ukrainian territory near Kyiv",
            "test-8", "bill"
        )
        ukr_mentions = [m for m in mentions if m.iso3 == "UKR"]
        assert len(ukr_mentions) == 1

    def test_empty_text(self, detector):
        mentions = detector.detect("", "test-9", "bill")
        assert mentions == []

    def test_no_countries_text(self, detector):
        mentions = detector.detect(
            "The committee met to discuss domestic policy issues",
            "test-10", "bill"
        )
        assert len(mentions) == 0


class TestTier0Blocklist:
    """Test Tier 0: Pre-filter blocklist."""

    def test_new_mexico_not_mexico(self, detector):
        """'New Mexico' should NOT trigger a Mexico match."""
        mentions = detector.detect(
            "The Senator from New Mexico introduced the bill",
            "test-bl-1", "crecord"
        )
        iso3s = [m.iso3 for m in mentions]
        assert "MEX" not in iso3s

    def test_new_jersey_not_jersey(self, detector):
        mentions = detector.detect(
            "Representative from New Jersey spoke",
            "test-bl-2", "crecord"
        )
        # Should not match Jersey (the island)
        iso3s = [m.iso3 for m in mentions]
        assert "JEY" not in iso3s

    def test_district_of_columbia_not_colombia(self, detector):
        mentions = detector.detect(
            "The District of Columbia Statehood Act",
            "test-bl-3", "bill"
        )
        iso3s = [m.iso3 for m in mentions]
        assert "COL" not in iso3s

    def test_west_virginia_not_virginia(self, detector):
        """'West Virginia' should be blocked as a unit."""
        mentions = detector.detect(
            "The gentleman from West Virginia yields five minutes",
            "test-bl-4", "crecord"
        )
        # Should not count as any country
        iso3s = [m.iso3 for m in mentions]
        # Virginia isn't a country anyway, but West Virginia
        # should be cleanly removed
        assert len(mentions) == 0


class TestWordBoundaries:
    """Test word boundary enforcement."""

    def test_iran_not_in_iranian(self, detector):
        """'Iran' and 'Iranian' should be separate matches, not overlapping."""
        mentions = detector.detect(
            "Iranian diplomats met in Tehran",
            "test-wb-1", "hearing"
        )
        # Should match Iran (via 'Iranian' demonym), not double-count
        iso3s = [m.iso3 for m in mentions]
        assert "IRN" in iso3s
        assert len([m for m in mentions if m.iso3 == "IRN"]) == 1

    def test_no_partial_match_inside_word(self, detector):
        """Country names inside larger words should not match."""
        mentions = detector.detect(
            "The organization handled the situation",
            "test-wb-2", "bill"
        )
        # "Iran" is inside "organization" — should not match
        iso3s = [m.iso3 for m in mentions]
        assert "IRN" not in iso3s


class TestPossessivesAndHyphens:
    """Test handling of possessive forms and hyphenated compounds."""

    def test_possessive_form(self, detector):
        """'Ukraine's' should match Ukraine."""
        mentions = detector.detect(
            "Ukraine's counteroffensive gained momentum",
            "test-pos-1", "hearing"
        )
        iso3s = [m.iso3 for m in mentions]
        assert "UKR" in iso3s

    def test_hyphenated_compound(self, detector):
        """'US-China' should match China."""
        mentions = detector.detect(
            "The US-China trade agreement was discussed",
            "test-hyp-1", "bill"
        )
        iso3s = [m.iso3 for m in mentions]
        assert "CHN" in iso3s


class TestMentionMetadata:
    """Test that mentions carry correct metadata."""

    def test_mention_has_tier(self, detector):
        mentions = detector.detect(
            "Afghanistan security situation",
            "test-meta-1", "hearing"
        )
        assert len(mentions) > 0
        assert mentions[0].tier == 1  # unambiguous = tier 1

    def test_mention_has_record_id(self, detector):
        mentions = detector.detect(
            "The situation in Iraq",
            "bill-118-hr1234", "bill"
        )
        assert mentions[0].record_id == "bill-118-hr1234"

    def test_mention_has_source_type(self, detector):
        mentions = detector.detect(
            "Syrian refugees",
            "test-meta-3", "hearing"
        )
        assert mentions[0].source_type == "hearing"
