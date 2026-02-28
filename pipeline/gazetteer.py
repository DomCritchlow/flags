"""Gazetteer loader — reads YAML files, builds lookup structures and Aho-Corasick automaton."""

import re
from pathlib import Path
from typing import Optional

import ahocorasick
import yaml

from pipeline import config


class GazetteerValidationError(Exception):
    pass


class Gazetteer:
    """Loads all gazetteer YAML files and builds lookup structures for detection."""

    def __init__(self, gazetteer_dir: Optional[Path] = None):
        self.gazetteer_dir = gazetteer_dir or config.GAZETTEER_DIR

        # Master data
        self.countries: dict[str, dict] = {}  # iso3 -> {name, iso2, region}
        self.unambiguous_terms: dict[str, str] = {}  # term -> iso3
        self.ambiguous_terms: dict[str, dict] = {}  # lowercase_key -> full config
        self.blocklist_phrases: list[str] = []
        self.procedural_strips: list[str] = []

        # Built structures
        self.automaton: Optional[ahocorasick.Automaton] = None

        self._load_all()
        self._build_automaton()

    def _load_all(self):
        """Load all YAML gazetteer files."""
        self._load_countries()
        self._load_unambiguous()
        self._load_ambiguous()
        self._load_blocklist()

    def _load_countries(self):
        """Load master country registry."""
        path = self.gazetteer_dir / "countries.yaml"
        if not path.exists():
            return
        data = yaml.safe_load(path.read_text())
        if data:
            for entry in data:
                self.countries[entry["iso3"]] = {
                    "name": entry["name"],
                    "iso2": entry["iso2"],
                    "region": entry.get("region", ""),
                }

    def _load_unambiguous(self):
        """Load unambiguous terms and build flat term->iso3 dictionary."""
        path = self.gazetteer_dir / "unambiguous_terms.yaml"
        if not path.exists():
            return
        data = yaml.safe_load(path.read_text())
        if not data:
            return

        for _key, entry in data.items():
            iso3 = entry["iso3"]
            terms = entry.get("terms", {})
            for category in ["names", "demonyms", "cities", "historical", "acronyms"]:
                for term in terms.get(category, []):
                    if term in self.unambiguous_terms:
                        existing = self.unambiguous_terms[term]
                        if existing != iso3:
                            raise GazetteerValidationError(
                                f"Term collision: '{term}' maps to both "
                                f"{existing} and {iso3}"
                            )
                    self.unambiguous_terms[term] = iso3

    def _load_ambiguous(self):
        """Load ambiguous terms with disambiguation rules."""
        path = self.gazetteer_dir / "ambiguous_terms.yaml"
        if not path.exists():
            return
        data = yaml.safe_load(path.read_text())
        if data:
            for key, entry in data.items():
                self.ambiguous_terms[key] = entry
                # Also register any explicit country_terms for exact matching
                if "country_terms" in entry:
                    for term in entry["country_terms"]:
                        # These are handled specially by the disambiguator,
                        # not the Aho-Corasick automaton
                        pass

    def _load_blocklist(self):
        """Load congressional blocklist phrases."""
        path = self.gazetteer_dir / "congressional_blocklist.yaml"
        if not path.exists():
            return
        data = yaml.safe_load(path.read_text())
        if data:
            self.blocklist_phrases = data.get("blocklist_phrases", [])
            self.procedural_strips = data.get("procedural_strips", [])

    def _build_automaton(self):
        """Build Aho-Corasick automaton from unambiguous terms."""
        self.automaton = ahocorasick.Automaton()
        for term, iso3 in self.unambiguous_terms.items():
            self.automaton.add_word(term, (term, iso3))

        # Also add trigger words for ambiguous terms
        # (the detector will route these to the disambiguator)
        for key, entry in self.ambiguous_terms.items():
            # Use the key as the primary trigger term (capitalized)
            trigger = key.capitalize()
            if "country_terms" in entry:
                for term in entry["country_terms"]:
                    self.automaton.add_word(
                        term, (term, f"AMBIGUOUS:{key}")
                    )
            elif "full_names" in entry:
                # Multi-country entries (e.g., Guinea variants)
                for fn in entry["full_names"]:
                    self.automaton.add_word(
                        fn["term"], (fn["term"], fn["iso3"])
                    )
                # Also add the bare trigger for routing to disambiguator
                self.automaton.add_word(
                    trigger, (trigger, f"AMBIGUOUS:{key}")
                )
            else:
                self.automaton.add_word(
                    trigger, (trigger, f"AMBIGUOUS:{key}")
                )

        if len(self.automaton) > 0:
            self.automaton.make_automaton()

    def is_ambiguous(self, iso3_or_tag: str) -> bool:
        """Check if a match result is an ambiguous term needing disambiguation."""
        return iso3_or_tag.startswith("AMBIGUOUS:")

    def get_ambiguous_key(self, tag: str) -> str:
        """Extract the ambiguous term key from an AMBIGUOUS: tag."""
        return tag.split(":", 1)[1]

    def get_ambiguous_config(self, key: str) -> dict:
        """Get full disambiguation config for an ambiguous term."""
        return self.ambiguous_terms.get(key, {})

    def validate(self) -> list[str]:
        """Run comprehensive validation checks. Returns list of issues."""
        issues = []

        # Check all unambiguous iso3 codes exist in countries registry
        for term, iso3 in self.unambiguous_terms.items():
            if iso3 not in self.countries:
                issues.append(
                    f"Unambiguous term '{term}' references unknown "
                    f"iso3 '{iso3}'"
                )

        # Check ambiguous iso3 codes
        for key, entry in self.ambiguous_terms.items():
            iso3 = entry.get("country_iso3")
            if iso3 and iso3 not in self.countries:
                issues.append(
                    f"Ambiguous term '{key}' references unknown "
                    f"iso3 '{iso3}'"
                )

        # Check for terms appearing in both unambiguous and ambiguous
        ambiguous_triggers = set()
        for key in self.ambiguous_terms:
            ambiguous_triggers.add(key.capitalize())
        for term in self.unambiguous_terms:
            if term.lower() in self.ambiguous_terms:
                issues.append(
                    f"Term '{term}' appears in both unambiguous and "
                    f"ambiguous gazetteers"
                )

        return issues

    def stats(self) -> dict:
        """Return coverage statistics."""
        return {
            "total_countries": len(self.countries),
            "unambiguous_terms": len(self.unambiguous_terms),
            "ambiguous_entries": len(self.ambiguous_terms),
            "blocklist_phrases": len(self.blocklist_phrases),
            "automaton_size": len(self.automaton) if self.automaton else 0,
        }
