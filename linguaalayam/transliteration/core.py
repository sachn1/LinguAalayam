"""Transliteration helpers for Malayalam ↔ Roman script conversion."""

import unicodedata

from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from ml2en.ml2en import ml2en as _ML2EN

# Schemes tried in order when attempting to interpret Latin input as Malayalam.
# None maps informal Manglish perfectly (no standard exists), but together they
# cover formal/scholarly romanisations that some users and tools produce.
_ROMAN_TO_ML_SCHEMES = [
    sanscript.ITRANS,
    sanscript.HK,
    sanscript.ISO,
]

_ml2en = _ML2EN()


def malayalam_to_roman(text: str) -> str:
    """Transliterate a Malayalam string to informal Roman script (ml2en)."""
    return _ml2en.transliterate(text).lower()


def normalize_roman(text: str) -> str:
    """Strip diacritics and lowercase a romanised string for approximate matching.

    Converts e.g. ``'ōṭuka'`` → ``'otuka'``, reducing the gap between ISO 15919
    output and informal Manglish spellings like ``'oduka'``.
    """
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()


def is_latin_script(text: str) -> bool:
    """Return True if every alphabetic character in *text* is ASCII (Latin script).

    Used to detect whether a search query is in Latin / Manglish rather than
    Malayalam Unicode (U+0D00–U+0D7F).
    """
    return bool(text) and all(ord(c) < 256 for c in text if c.isalpha())


def roman_to_malayalam_candidates(text: str) -> list[str]:
    """Return distinct Malayalam transliterations of a Latin-script string.

    Tries each scheme in :data:`_ROMAN_TO_ML_SCHEMES` and returns unique
    results that differ from the input (i.e. actually produced Malayalam).
    Results are ordered by scheme priority.

    Note: informal Manglish (e.g. ``'oduka'``) is not reliably handled by any
    standard scheme.  Use these candidates for exact/fuzzy DB lookup; fall back
    to semantic search when all candidates miss.
    """
    seen: set[str] = set()
    candidates: list[str] = []
    for scheme in _ROMAN_TO_ML_SCHEMES:
        try:
            result = transliterate(text, scheme, sanscript.MALAYALAM)
        except Exception:
            continue
        if result and result != text and result not in seen:
            seen.add(result)
            candidates.append(result)
    return candidates
