"""Tests for Tier 2 rule-based disambiguation."""

import pytest
from pipeline.gazetteer import Gazetteer
from pipeline.disambiguator import Disambiguator


@pytest.fixture
def gazetteer():
    return Gazetteer()


@pytest.fixture
def disambiguator(gazetteer):
    return Disambiguator(gazetteer)


class TestGeorgiaDisambiguation:
    """Georgia: US state vs. country in the Caucasus."""

    def test_state_context_gentleman_from(self, disambiguator):
        result = disambiguator.disambiguate(
            "Georgia", "georgia",
            "the gentleman from Georgia yields five minutes to the ranking member",
            "test-ga-1", "crecord"
        )
        assert result.decision in ("NOT_COUNTRY", "SKIP")

    def test_state_context_atlanta(self, disambiguator):
        result = disambiguator.disambiguate(
            "Georgia", "georgia",
            "The city of Atlanta, Georgia has experienced significant growth",
            "test-ga-2", "crecord"
        )
        assert result.decision in ("NOT_COUNTRY", "SKIP")

    def test_country_context_tbilisi(self, disambiguator):
        result = disambiguator.disambiguate(
            "Georgia", "georgia",
            "The situation in Georgia following protests in Tbilisi against the Russian-backed government",
            "test-ga-3", "hearing"
        )
        assert result.decision == "COUNTRY"
        assert result.iso3 == "GEO"

    def test_country_context_caucasus(self, disambiguator):
        result = disambiguator.disambiguate(
            "Georgia", "georgia",
            "Georgia and the broader Caucasus region face threats from Russian annexation",
            "test-ga-4", "hearing"
        )
        assert result.decision == "COUNTRY"

    def test_default_is_state(self, disambiguator):
        """With no context signals, Georgia should default to state (NOT_COUNTRY)."""
        result = disambiguator.disambiguate(
            "Georgia", "georgia",
            "Georgia is mentioned in the document",
            "test-ga-5", "bill"
        )
        assert result.decision in ("NOT_COUNTRY", "SKIP")


class TestJordanDisambiguation:
    """Jordan: Jim Jordan (Rep) vs. the country."""

    def test_person_jim_jordan(self, disambiguator):
        result = disambiguator.disambiguate(
            "Jordan", "jordan",
            "Mr. Jordan of Ohio asked the witness to clarify the timeline",
            "test-jo-1", "crecord"
        )
        assert result.decision in ("NOT_COUNTRY", "SKIP")

    def test_person_chairman_jordan(self, disambiguator):
        result = disambiguator.disambiguate(
            "Jordan", "jordan",
            "Chairman Jordan convened the subcommittee hearing on oversight",
            "test-jo-2", "hearing"
        )
        assert result.decision in ("NOT_COUNTRY", "SKIP")

    def test_country_amman(self, disambiguator):
        result = disambiguator.disambiguate(
            "Jordan", "jordan",
            "King Abdullah of Jordan met with officials in Amman to discuss the peace process",
            "test-jo-3", "hearing"
        )
        assert result.decision == "COUNTRY"
        assert result.iso3 == "JOR"

    def test_country_hashemite(self, disambiguator):
        result = disambiguator.disambiguate(
            "Jordan", "jordan",
            "The Hashemite Kingdom of Jordan plays a key role in Middle East stability",
            "test-jo-4", "bill"
        )
        assert result.decision == "COUNTRY"


class TestTurkeyDisambiguation:
    """Turkey: the bird vs. the country."""

    def test_country_default(self, disambiguator):
        """Turkey should default to COUNTRY in congressional context."""
        result = disambiguator.disambiguate(
            "Turkey", "turkey",
            "Turkey has been a NATO ally for decades",
            "test-tu-1", "hearing"
        )
        assert result.decision == "COUNTRY"

    def test_country_ankara(self, disambiguator):
        result = disambiguator.disambiguate(
            "Turkey", "turkey",
            "Relations with Turkey deteriorated after the Ankara government",
            "test-tu-2", "bill"
        )
        assert result.decision == "COUNTRY"

    def test_not_country_thanksgiving(self, disambiguator):
        result = disambiguator.disambiguate(
            "Turkey", "turkey",
            "Thanksgiving turkey dinner for military families",
            "test-tu-3", "crecord"
        )
        assert result.decision in ("NOT_COUNTRY", "SKIP")


class TestColombiaSepellingMatch:
    """Colombia/Columbia: exact spelling disambiguation."""

    def test_colombia_is_country(self, disambiguator):
        result = disambiguator.disambiguate(
            "Colombia", "colombia",
            "Assistance to Colombia for counter-narcotics operations",
            "test-col-1", "bill"
        )
        assert result.decision == "COUNTRY"
        assert result.iso3 == "COL"

    def test_columbia_is_not_country(self, disambiguator):
        result = disambiguator.disambiguate(
            "Columbia", "colombia",
            "Columbia University released a new study",
            "test-col-2", "crecord"
        )
        assert result.decision == "NOT_COUNTRY"


class TestChadDisambiguation:
    """Chad: first name vs. country."""

    def test_default_skip(self, disambiguator):
        """Bare 'Chad' should default to SKIP."""
        result = disambiguator.disambiguate(
            "Chad", "chad",
            "Chad mentioned the importance of bipartisan cooperation",
            "test-ch-1", "crecord"
        )
        assert result.decision == "SKIP"

    def test_country_ndjamena(self, disambiguator):
        result = disambiguator.disambiguate(
            "Chad", "chad",
            "The Republic of Chad with its capital N'Djamena faces instability in the Sahel",
            "test-ch-2", "hearing"
        )
        assert result.decision == "COUNTRY"
        assert result.iso3 == "TCD"


class TestGuineaMultiCountry:
    """Guinea: requires full name to distinguish variants."""

    def test_bare_guinea_skipped(self, disambiguator):
        """Bare 'Guinea' should be skipped."""
        result = disambiguator.disambiguate(
            "Guinea", "guinea",
            "The Guinea coast experienced heavy rainfall",
            "test-gu-1", "crecord"
        )
        assert result.decision == "SKIP"


class TestScoringBoundaries:
    """Test that scoring thresholds work correctly."""

    def test_strong_signal_exceeds_threshold(self, disambiguator):
        """A single strong country signal (+10) should push above threshold (5)."""
        result = disambiguator.disambiguate(
            "Georgia", "georgia",
            "Tbilisi was the site of major protests",
            "test-score-1", "hearing"
        )
        assert result.score >= 10
        assert result.decision == "COUNTRY"

    def test_strong_non_country_signal(self, disambiguator):
        """A single strong non-country signal (-10) should push below threshold (-5)."""
        result = disambiguator.disambiguate(
            "Georgia", "georgia",
            "the gentleman from Georgia spoke at length about the issue in Atlanta",
            "test-score-2", "crecord"
        )
        assert result.score <= -10
        assert result.decision == "NOT_COUNTRY"
