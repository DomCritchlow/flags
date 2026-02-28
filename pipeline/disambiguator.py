"""Tier 2: Rule-based contextual disambiguation.

For ambiguous terms (~20 terms that could refer to a country or something else),
examines a context window and scores against signal lists.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from pipeline import config


@dataclass
class DisambiguationResult:
    """Result of a disambiguation attempt."""
    term: str
    key: str  # ambiguous term key
    decision: str  # COUNTRY, NOT_COUNTRY, SKIP, or TIER3
    iso3: Optional[str] = None
    score: float = 0.0
    reason: str = ""
    record_id: str = ""


class Disambiguator:
    """Tier 2 rule-based scorer for ambiguous terms."""

    def __init__(self, gazetteer):
        self.gazetteer = gazetteer

    def disambiguate(
        self,
        term: str,
        key: str,
        full_text: str,
        record_id: str,
        source_type: str,
    ) -> DisambiguationResult:
        """Disambiguate an ambiguous term using context signals.

        Returns a DisambiguationResult with decision:
        - COUNTRY: term refers to the country
        - NOT_COUNTRY: term does not refer to a country
        - SKIP: too ambiguous, don't count
        - TIER3: inconclusive, needs LLM fallback
        """
        entry = self.gazetteer.get_ambiguous_config(key)
        if not entry:
            return DisambiguationResult(
                term=term, key=key, decision="SKIP",
                reason="No disambiguation config found",
                record_id=record_id,
            )

        iso3 = entry.get("country_iso3", "")

        # Special case: exact spelling match (Colombia/Columbia)
        if entry.get("matching_rule") == "EXACT_SPELLING":
            return self._exact_spelling_match(
                term, key, entry, record_id
            )

        # Special case: require full name (Guinea, Congo, Dominica, Marshall)
        if entry.get("require_full_name"):
            return self._require_full_name(
                term, key, entry, full_text, record_id
            )

        # Standard scoring: extract context window and score
        context = self._extract_context(term, full_text)
        score = self._score_context(context, entry)
        default = entry.get("default", "SKIP")

        if score > config.DISAMBIGUATION_THRESHOLD_COUNTRY:
            decision = "COUNTRY"
            reason = f"Score {score} > threshold {config.DISAMBIGUATION_THRESHOLD_COUNTRY}"
        elif score < config.DISAMBIGUATION_THRESHOLD_NOT_COUNTRY:
            decision = "NOT_COUNTRY"
            reason = f"Score {score} < threshold {config.DISAMBIGUATION_THRESHOLD_NOT_COUNTRY}"
        elif default == "COUNTRY":
            decision = "COUNTRY"
            reason = f"Score {score} inconclusive, using default: COUNTRY"
        elif default in ("STATE", "PERSON"):
            decision = "NOT_COUNTRY"
            reason = f"Score {score} inconclusive, using default: {default}"
        elif default == "SKIP":
            decision = "SKIP"
            reason = f"Score {score} inconclusive, default is SKIP"
        else:
            decision = "TIER3"
            reason = f"Score {score} inconclusive, escalating to Tier 3"

        result = DisambiguationResult(
            term=term,
            key=key,
            decision=decision,
            iso3=iso3 if decision == "COUNTRY" else None,
            score=score,
            reason=reason,
            record_id=record_id,
        )

        self._log_decision(result, context, source_type)
        return result

    def _exact_spelling_match(
        self, term: str, key: str, entry: dict, record_id: str
    ) -> DisambiguationResult:
        """Handle Colombia/Columbia style exact spelling disambiguation."""
        country_terms = entry.get("country_terms", [])
        never_terms = entry.get("never_country_terms", [])

        if term in country_terms:
            return DisambiguationResult(
                term=term, key=key, decision="COUNTRY",
                iso3=entry.get("country_iso3"),
                reason=f"Exact spelling match: '{term}' is a country term",
                record_id=record_id,
            )
        elif term in never_terms:
            return DisambiguationResult(
                term=term, key=key, decision="NOT_COUNTRY",
                reason=f"Exact spelling match: '{term}' is a non-country term",
                record_id=record_id,
            )
        else:
            return DisambiguationResult(
                term=term, key=key, decision="SKIP",
                reason=f"Spelling '{term}' not in either list",
                record_id=record_id,
            )

    def _require_full_name(
        self, term: str, key: str, entry: dict,
        full_text: str, record_id: str
    ) -> DisambiguationResult:
        """Handle terms that require a full compound name (Guinea, Congo, etc.)."""
        full_names = entry.get("full_names", [])

        # Check if the matched term IS one of the full names
        for fn in full_names:
            if fn["term"] == term:
                return DisambiguationResult(
                    term=term, key=key, decision="COUNTRY",
                    iso3=fn["iso3"],
                    reason=f"Full name match: '{term}'",
                    record_id=record_id,
                )

        # Check if any full name appears in surrounding text
        for fn in full_names:
            if fn["term"] in full_text:
                # The full name exists — the bare term was probably part of it
                # (already caught by longest-match in Aho-Corasick)
                return DisambiguationResult(
                    term=term, key=key, decision="SKIP",
                    reason=f"Bare term '{term}' with full name '{fn['term']}' in text",
                    record_id=record_id,
                )

        # Bare term with no full name context — skip
        return DisambiguationResult(
            term=term, key=key, decision="SKIP",
            reason=f"Bare term '{term}' with no qualifying full name in context",
            record_id=record_id,
        )

    def _extract_context(self, term: str, full_text: str) -> str:
        """Extract ±N words around the first occurrence of term."""
        idx = full_text.find(term)
        if idx == -1:
            return full_text[:200]  # fallback: first 200 chars

        # Find word boundaries around the match
        words_before = full_text[:idx].split()
        words_after = full_text[idx + len(term):].split()

        n = config.CONTEXT_WINDOW_WORDS
        context_before = " ".join(words_before[-n:])
        context_after = " ".join(words_after[:n])

        return f"{context_before} {term} {context_after}"

    def _score_context(self, context: str, entry: dict) -> float:
        """Score a context window against signal lists."""
        score = 0.0

        country_signals = entry.get("country_signals", {})
        non_country_signals = entry.get("non_country_signals", {})

        # Country signals
        for signal in country_signals.get("strong", []):
            if self._signal_matches(signal, context):
                score += config.SIGNAL_WEIGHT_STRONG
        for signal in country_signals.get("moderate", []):
            if self._signal_matches(signal, context):
                score += config.SIGNAL_WEIGHT_MODERATE

        # Non-country signals
        for signal in non_country_signals.get("strong", []):
            if self._signal_matches(signal, context):
                score -= config.SIGNAL_WEIGHT_STRONG
        for signal in non_country_signals.get("moderate", []):
            if self._signal_matches(signal, context):
                score -= config.SIGNAL_WEIGHT_MODERATE

        return score

    def _signal_matches(self, signal: str, context: str) -> bool:
        """Check if a signal matches in the context. Signals can be regex patterns."""
        try:
            # Try as regex first (some signals have patterns like "[0-9]")
            if any(c in signal for c in r"[]\^$.|?*+(){}"):
                return bool(re.search(signal, context))
            else:
                return signal in context
        except re.error:
            # If regex compilation fails, do plain string match
            return signal in context

    def _log_decision(
        self, result: DisambiguationResult, context: str, source_type: str
    ):
        """Append disambiguation decision to audit log."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "term": result.term,
            "key": result.key,
            "decision": result.decision,
            "score": result.score,
            "reason": result.reason,
            "record_id": result.record_id,
            "source_type": source_type,
            "context_snippet": context[:200],
        }
        try:
            config.AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(config.AUDIT_LOG_PATH, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except OSError:
            pass  # Don't fail detection if audit logging fails
