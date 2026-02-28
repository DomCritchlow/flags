"""Tier 3: LLM fallback for unresolvable disambiguation cases.

Uses Claude Haiku for binary classification of ambiguous terms.
Results are cached to avoid redundant API calls.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from pipeline import config
from pipeline.disambiguator import DisambiguationResult

logger = logging.getLogger(__name__)


class LLMFallback:
    """Tier 3 LLM-based disambiguation using Claude Haiku."""

    PROMPT_TEMPLATE = """You are classifying whether a term refers to a country or something else.

Term: "{term}"
Full context: "...{context}..."
Source: {source_type}

Does "{term}" refer to the country in this context?
Respond with exactly one word: COUNTRY or OTHER"""

    def __init__(self, cache_path: Optional[Path] = None):
        self.cache_path = cache_path or config.LLM_CACHE_PATH
        self._cache = self._load_cache()
        self._client = None  # lazy init

    def _load_cache(self) -> dict:
        """Load LLM result cache from disk."""
        if self.cache_path.exists():
            try:
                return json.loads(self.cache_path.read_text())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_cache(self):
        """Persist LLM result cache to disk."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self._cache, indent=2))
        except OSError as e:
            logger.warning(f"Failed to save LLM cache: {e}")

    def _get_client(self):
        """Lazily initialize the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(
                    api_key=config.ANTHROPIC_API_KEY
                )
            except ImportError:
                logger.error("anthropic package not installed")
                return None
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                return None
        return self._client

    def classify(
        self,
        term: str,
        key: str,
        full_text: str,
        record_id: str,
        source_type: str,
        ambiguous_config: dict,
    ) -> Optional[DisambiguationResult]:
        """Classify an ambiguous term using the LLM.

        Returns DisambiguationResult or None if classification fails.
        """
        # Check cache
        cache_key = f"{term}:{record_id}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            return DisambiguationResult(
                term=term,
                key=key,
                decision=cached["decision"],
                iso3=ambiguous_config.get("country_iso3") if cached["decision"] == "COUNTRY" else None,
                score=0.0,
                reason=f"LLM (cached): {cached['decision']}",
                record_id=record_id,
            )

        # Extract context window (~100 words around the term)
        idx = full_text.find(term)
        if idx == -1:
            context = full_text[:500]
        else:
            words_before = full_text[:idx].split()
            words_after = full_text[idx + len(term):].split()
            context_before = " ".join(words_before[-50:])
            context_after = " ".join(words_after[:50])
            context = f"{context_before} {term} {context_after}"

        # Call LLM
        prompt = self.PROMPT_TEMPLATE.format(
            term=term,
            context=context[:500],
            source_type=source_type,
        )

        client = self._get_client()
        if not client:
            # Fallback to default when API unavailable
            return self._use_default(term, key, ambiguous_config, record_id)

        try:
            response = client.messages.create(
                model=config.LLM_MODEL,
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}],
            )
            answer = response.content[0].text.strip().upper()

            if answer == "COUNTRY":
                decision = "COUNTRY"
            else:
                decision = "NOT_COUNTRY"

            # Cache result
            self._cache[cache_key] = {"decision": decision}
            self._save_cache()

            iso3 = ambiguous_config.get("country_iso3") if decision == "COUNTRY" else None

            return DisambiguationResult(
                term=term,
                key=key,
                decision=decision,
                iso3=iso3,
                score=0.0,
                reason=f"LLM Tier 3: {answer}",
                record_id=record_id,
            )

        except Exception as e:
            logger.warning(f"LLM fallback failed for '{term}' in {record_id}: {e}")
            return self._use_default(term, key, ambiguous_config, record_id)

    def _use_default(
        self, term: str, key: str, ambiguous_config: dict, record_id: str
    ) -> Optional[DisambiguationResult]:
        """Fall back to the term's default when LLM is unavailable."""
        default = ambiguous_config.get("default", "SKIP")

        if default == "COUNTRY":
            decision = "COUNTRY"
            iso3 = ambiguous_config.get("country_iso3")
        elif default in ("STATE", "PERSON"):
            decision = "NOT_COUNTRY"
            iso3 = None
        else:
            decision = "SKIP"
            iso3 = None

        return DisambiguationResult(
            term=term,
            key=key,
            decision=decision,
            iso3=iso3,
            score=0.0,
            reason=f"LLM unavailable, using default: {default}",
            record_id=record_id,
        )
