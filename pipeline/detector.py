"""Country detection engine — 3-tier detection pipeline.

Tier 0: Blocklist pre-filter (mask false-positive phrases)
Tier 1: Aho-Corasick unambiguous dictionary match
Tier 2: Rule-based contextual disambiguation
Tier 3: LLM fallback for unresolvable cases
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from pipeline import config
from pipeline.gazetteer import Gazetteer
from pipeline.disambiguator import Disambiguator, DisambiguationResult
from pipeline.llm_fallback import LLMFallback


@dataclass
class Match:
    """A raw match from the Aho-Corasick scan."""
    term: str
    iso3_or_tag: str  # iso3 code or "AMBIGUOUS:key"
    start: int  # character offset in cleaned text
    end: int  # character offset end


@dataclass
class Mention:
    """A confirmed country mention."""
    iso3: str
    country_name: str
    term: str  # the matched term
    record_id: str
    source_type: str
    tier: int  # which tier confirmed this (1, 2, or 3)
    score: Optional[float] = None  # disambiguation score if tier 2/3
    month: str = ""  # YYYY-MM, set by caller

    def to_dict(self) -> dict:
        return {
            "iso3": self.iso3,
            "country_name": self.country_name,
            "term": self.term,
            "record_id": self.record_id,
            "source_type": self.source_type,
            "tier": self.tier,
            "score": self.score,
            "month": self.month,
        }


class CountryDetector:
    """Orchestrates the 3-tier country detection pipeline."""

    def __init__(self, gazetteer: Gazetteer, enable_llm: bool = True):
        self.gazetteer = gazetteer
        self.disambiguator = Disambiguator(gazetteer)
        self.llm_fallback = LLMFallback() if enable_llm else None
        self._blocklist_patterns = self._compile_blocklist()

    def _compile_blocklist(self) -> list[re.Pattern]:
        """Compile blocklist phrases into regex patterns for masking."""
        patterns = []
        for phrase in self.gazetteer.blocklist_phrases:
            if "{STATE}" in phrase:
                # Template pattern — skip, handled separately
                continue
            # Escape regex special chars, enforce word boundaries
            escaped = re.escape(phrase)
            patterns.append(re.compile(r"\b" + escaped + r"\b", re.IGNORECASE))

        # Compile procedural strip patterns
        us_states = [
            "Alabama", "Alaska", "Arizona", "Arkansas", "California",
            "Colorado", "Connecticut", "Delaware", "Florida", "Georgia",
            "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas",
            "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts",
            "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana",
            "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
            "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma",
            "Oregon", "Pennsylvania", "Rhode Island", "South Carolina",
            "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
            "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
        ]
        for template in self.gazetteer.procedural_strips:
            if "{STATE}" in template:
                for state in us_states:
                    phrase = template.replace("{STATE}", state)
                    escaped = re.escape(phrase)
                    patterns.append(re.compile(escaped, re.IGNORECASE))
        return patterns

    def detect(
        self, text: str, record_id: str, source_type: str
    ) -> list[Mention]:
        """Run full 3-tier detection on text. Returns deduplicated mentions."""
        if not text or not text.strip():
            return []

        # Tier 0: Apply blocklist pre-filter
        cleaned = self._apply_blocklist(text)

        # Strip possessives for matching
        cleaned = self._normalize_possessives(cleaned)

        # Tier 1: Aho-Corasick scan
        raw_matches = self._tier1_scan(cleaned)

        # Filter to longest non-overlapping matches at word boundaries
        matches = self._filter_matches(raw_matches, cleaned)

        # Process matches through tiers
        mentions = []
        tier3_candidates = []

        for match in matches:
            if self.gazetteer.is_ambiguous(match.iso3_or_tag):
                # Tier 2: Disambiguation
                key = self.gazetteer.get_ambiguous_key(match.iso3_or_tag)
                result = self.disambiguator.disambiguate(
                    match.term, key, cleaned, record_id, source_type
                )
                if result.decision == "COUNTRY":
                    mention = self._make_mention(
                        result.iso3, match.term, record_id,
                        source_type, tier=2, score=result.score
                    )
                    if mention:
                        mentions.append(mention)
                elif result.decision == "TIER3":
                    tier3_candidates.append((match, key))
                # NOT_COUNTRY and SKIP are dropped
            else:
                # Tier 1: Unambiguous match
                mention = self._make_mention(
                    match.iso3_or_tag, match.term, record_id,
                    source_type, tier=1
                )
                if mention:
                    mentions.append(mention)

        # Tier 3: LLM fallback for unresolved cases
        if tier3_candidates and self.llm_fallback:
            for match, key in tier3_candidates:
                result = self.llm_fallback.classify(
                    match.term, key, cleaned, record_id, source_type,
                    self.gazetteer.get_ambiguous_config(key)
                )
                if result and result.decision == "COUNTRY":
                    mention = self._make_mention(
                        result.iso3, match.term, record_id,
                        source_type, tier=3, score=result.score
                    )
                    if mention:
                        mentions.append(mention)

        # Deduplicate: one mention per country per record
        return self._deduplicate(mentions)

    def _apply_blocklist(self, text: str) -> str:
        """Mask blocklist phrases with same-length whitespace to preserve offsets."""
        result = text
        for pattern in self._blocklist_patterns:
            result = pattern.sub(
                lambda m: " " * len(m.group()), result
            )
        return result

    def _normalize_possessives(self, text: str) -> str:
        """Strip possessive suffixes for matching while preserving offsets."""
        # Replace 's with spaces (same length: 2 chars)
        return re.sub(r"'s\b", "  ", text)

    def _tier1_scan(self, text: str) -> list[Match]:
        """Run Aho-Corasick automaton over text. Returns all matches."""
        if not self.gazetteer.automaton or not len(self.gazetteer.automaton):
            return []

        matches = []
        for end_idx, (term, iso3_or_tag) in self.gazetteer.automaton.iter(text):
            start_idx = end_idx - len(term) + 1
            matches.append(Match(
                term=term,
                iso3_or_tag=iso3_or_tag,
                start=start_idx,
                end=end_idx + 1,
            ))
        return matches

    def _filter_matches(self, matches: list[Match], text: str) -> list[Match]:
        """Filter to longest non-overlapping matches at word boundaries."""
        if not matches:
            return []

        # First filter to word-boundary matches only
        boundary_matches = []
        for m in matches:
            if self._is_word_boundary(text, m.start, m.end):
                boundary_matches.append(m)

        if not boundary_matches:
            return []

        # Sort by start position, then by length descending (longest first)
        boundary_matches.sort(key=lambda m: (m.start, -(m.end - m.start)))

        # Greedy longest-match-first, no overlaps
        result = []
        last_end = -1
        for m in boundary_matches:
            if m.start >= last_end:
                result.append(m)
                last_end = m.end
            elif m.end - m.start > result[-1].end - result[-1].start and m.start == result[-1].start:
                # Longer match at same position replaces shorter
                result[-1] = m
                last_end = m.end

        return result

    def _is_word_boundary(self, text: str, start: int, end: int) -> bool:
        """Check that match is at word boundaries (not inside a larger word)."""
        # Check character before start
        if start > 0 and text[start - 1].isalnum():
            return False
        # Check character after end
        if end < len(text) and text[end].isalnum():
            return False
        return True

    def _make_mention(
        self, iso3: str, term: str, record_id: str,
        source_type: str, tier: int, score: Optional[float] = None
    ) -> Optional[Mention]:
        """Create a Mention object, looking up country name from gazetteer."""
        country_info = self.gazetteer.countries.get(iso3)
        if not country_info:
            return None
        return Mention(
            iso3=iso3,
            country_name=country_info["name"],
            term=term,
            record_id=record_id,
            source_type=source_type,
            tier=tier,
            score=score,
        )

    def _deduplicate(self, mentions: list[Mention]) -> list[Mention]:
        """Keep one mention per country per record."""
        seen = set()
        result = []
        for m in mentions:
            key = m.iso3
            if key not in seen:
                seen.add(key)
                result.append(m)
        return result
