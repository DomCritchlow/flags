"""Regression test suite for known false positive/negative cases.

Each test case is a real or realistic congressional text snippet with a
known correct answer. This suite grows over time as new edge cases are
discovered through monthly audit log reviews.
"""

import pytest
from pipeline.gazetteer import Gazetteer
from pipeline.detector import CountryDetector


@pytest.fixture
def detector():
    return CountryDetector(Gazetteer(), enable_llm=False)


# Each case: (text, term_of_interest, expected_present_as_country, record_id, notes)
KNOWN_CASES = [
    # === Georgia: US state cases (should NOT detect as country) ===
    {
        "text": "Mr. Jordan of Ohio asked the witness to clarify",
        "should_not_contain": ["JOR"],
        "id": "crecord-118-2024-03-15",
        "notes": "Jim Jordan is a Representative, not the country",
    },
    {
        "text": "the gentleman from Georgia yields five minutes",
        "should_not_contain": ["GEO"],
        "id": "crecord-117-2022-06-12",
        "notes": "US state Georgia in procedural speech",
    },
    {
        "text": "The Senator from Georgia introduced an amendment regarding Atlanta infrastructure",
        "should_not_contain": ["GEO"],
        "id": "crecord-118-2023-05-20",
        "notes": "Senator from Georgia (state)",
    },

    # === Georgia: country cases (SHOULD detect) ===
    {
        "text": "The situation in Georgia following the Russian invasion of South Ossetia",
        "should_contain": ["GEO"],
        "id": "hearing-110-2008-09",
        "notes": "Georgia the country (Caucasus context)",
    },

    # === Jordan: person name cases ===
    {
        "text": "Chairman Jordan convened the Judiciary Committee to hear testimony",
        "should_not_contain": ["JOR"],
        "id": "hearing-118-2024-01-15",
        "notes": "Jim Jordan as committee chair",
    },

    # === Jordan: country cases ===
    {
        "text": "King Abdullah of Jordan visited Washington to discuss the Hashemite Kingdom's role",
        "should_contain": ["JOR"],
        "id": "hearing-118-2024-02-10",
        "notes": "Jordan the country with clear signals",
    },

    # === Colombia/Columbia spelling ===
    {
        "text": "Providing assistance to Colombia to combat narcotics trafficking",
        "should_contain": ["COL"],
        "id": "bill-107-hr3421",
        "notes": "Colombia (with 'o') is always the country",
    },
    {
        "text": "the District of Columbia Statehood Act",
        "should_not_contain": ["COL"],
        "id": "bill-117-hr51",
        "notes": "Columbia (with 'u') in DC is never the country",
    },

    # === New Mexico blocklist ===
    {
        "text": "The Representative from New Mexico discussed border security",
        "should_not_contain": ["MEX"],
        "id": "crecord-118-2024-04-01",
        "notes": "New Mexico should not trigger Mexico",
    },

    # === Turkey disambiguation ===
    {
        "text": "Turkey's NATO membership and the situation in Ankara",
        "should_contain": ["TUR"],
        "id": "hearing-118-2024-03-01",
        "notes": "Turkey the country with NATO context",
    },

    # === Unambiguous country mentions ===
    {
        "text": "Ukraine Security Supplemental Appropriations Act",
        "should_contain": ["UKR"],
        "id": "bill-118-hr1234",
        "notes": "Clear unambiguous mention",
    },
    {
        "text": "Hearing on China's Military Modernization",
        "should_contain": ["CHN"],
        "id": "hearing-118-2024-02-20",
        "notes": "Clear unambiguous mention",
    },
    {
        "text": "The DPRK launched an intercontinental ballistic missile",
        "should_contain": ["PRK"],
        "id": "crecord-118-2024-01-05",
        "notes": "Acronym for North Korea",
    },
    {
        "text": "Iranian nuclear program poses ongoing threat",
        "should_contain": ["IRN"],
        "id": "hearing-118-2023-11-15",
        "notes": "Demonym match",
    },
    {
        "text": "The former state of Burma continues democratic backsliding as Myanmar",
        "should_contain": ["MMR"],
        "id": "hearing-117-2022-03-10",
        "notes": "Historical name (Burma) and current name (Myanmar)",
    },

    # === Multi-country mentions ===
    {
        "text": "Relations between Israel and Saudi Arabia normalized under the Abraham Accords",
        "should_contain": ["SAU"],
        "id": "hearing-118-2024-01-20",
        "notes": "Multi-country mention, both should be detected",
    },

    # === Word boundary tests ===
    {
        "text": "The organization handled the situation professionally",
        "should_not_contain": ["IRN"],
        "id": "crecord-118-2024-05-01",
        "notes": "'Iran' inside 'organization' should not match",
    },

    # === West Virginia blocklist ===
    {
        "text": "The Senator from West Virginia discussed coal mining",
        "should_not_contain": [],  # No countries should be detected
        "id": "crecord-118-2024-06-01",
        "notes": "West Virginia should not trigger any country match",
    },

    # === South Korea vs North Korea ===
    {
        "text": "South Korea and the United States conducted joint military exercises",
        "should_contain": ["KOR"],
        "should_not_contain": ["PRK"],
        "id": "hearing-118-2024-04-15",
        "notes": "South Korea should match ROK, not DPRK",
    },

    # === Chad: person name ===
    {
        "text": "Representative Chad Smith introduced the bill",
        "should_not_contain": ["TCD"],
        "id": "crecord-118-2024-07-01",
        "notes": "Chad as first name should not match the country",
    },

    # === Possessive forms ===
    {
        "text": "Ukraine's counteroffensive and the path forward",
        "should_contain": ["UKR"],
        "id": "hearing-118-2023-09-01",
        "notes": "Possessive form should still match",
    },

    # === Hyphenated compounds ===
    {
        "text": "The US-China trade war affected global markets",
        "should_contain": ["CHN"],
        "id": "hearing-118-2024-01-10",
        "notes": "Hyphenated compound should extract China",
    },

    # === British Columbia blocklist ===
    {
        "text": "Trade with British Columbia and the Pacific Northwest",
        "should_not_contain": ["COL"],
        "id": "hearing-118-2024-08-01",
        "notes": "British Columbia should not trigger Colombia",
    },

    # === India / Indian: Native American false positives ===
    {
        "text": "To amend the Act of June 18, 1934, to reaffirm the authority of the "
                "Secretary of the Interior to take land into trust for Indian tribes",
        "should_not_contain": ["IND"],
        "id": "bill-113-s1234",
        "notes": "Indian tribes = Native American context, not India",
    },
    {
        "text": "A bill to reauthorize the Indian Health Service and improve health care "
                "for American Indians and Alaska Natives",
        "should_not_contain": ["IND"],
        "id": "bill-115-s2474",
        "notes": "Indian Health Service is a domestic agency, not India",
    },
    {
        "text": "The Bureau of Indian Affairs shall consult with federally recognized tribes",
        "should_not_contain": ["IND"],
        "id": "bill-114-hr4300",
        "notes": "Bureau of Indian Affairs is a domestic agency",
    },
    {
        "text": "An act to provide for Indian self-determination and education assistance",
        "should_not_contain": ["IND"],
        "id": "bill-94-pl638",
        "notes": "Indian Self-Determination Act refers to Native Americans",
    },

    # === India / Indian: country cases (SHOULD detect) ===
    {
        "text": "The United States and India signed a civil nuclear agreement "
                "following Prime Minister Modi's visit to Washington",
        "should_contain": ["IND"],
        "id": "bill-114-hr1190",
        "notes": "India the country, Modi context",
    },
    {
        "text": "India's parliament approved new legislation affecting trade relations "
                "with the United States and New Delhi signaled support",
        "should_contain": ["IND"],
        "id": "hearing-116-2019-02",
        "notes": "India the country, parliament + New Delhi context",
    },
]


class TestKnownFalsePositives:
    """Regression tests for known edge cases."""

    @pytest.mark.parametrize(
        "case",
        KNOWN_CASES,
        ids=[c["id"] for c in KNOWN_CASES],
    )
    def test_known_case(self, detector, case):
        mentions = detector.detect(case["text"], case["id"], "test")
        detected_iso3s = {m.iso3 for m in mentions}

        # Check expected countries ARE detected
        for iso3 in case.get("should_contain", []):
            assert iso3 in detected_iso3s, (
                f"Expected {iso3} in '{case['text']}' "
                f"(got {detected_iso3s}). Notes: {case['notes']}"
            )

        # Check expected countries are NOT detected
        for iso3 in case.get("should_not_contain", []):
            assert iso3 not in detected_iso3s, (
                f"Unexpected {iso3} in '{case['text']}' "
                f"(got {detected_iso3s}). Notes: {case['notes']}"
            )
