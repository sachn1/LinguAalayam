"""Transliteration utilities — Manglish, romanisation, and morphological analysis."""

from .core import is_latin_script, malayalam_to_roman, normalize_roman, roman_to_malayalam_candidates
from .morphology import analyse_word
from .varnam import manglish_to_malayalam

__all__ = [
    "is_latin_script",
    "malayalam_to_roman",
    "normalize_roman",
    "roman_to_malayalam_candidates",
    "analyse_word",
    "manglish_to_malayalam",
]
