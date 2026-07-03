"""Morphological analysis for Malayalam words using mlmorph."""

import re
from functools import lru_cache

from mlmorph import Analyser

_analyser = None

_POS = {
    "v": "verb",
    "n": "noun",
    "np": "proper noun",
    "adj": "adjective",
    "adv": "adverb",
    "num": "numeral",
    "pron": "pronoun",
    "conj": "conjunction",
    "post": "postposition",
    "part": "particle",
    "intj": "interjection",
}

_FEATURES = {
    "past": "past",
    "present": "present",
    "future": "future",
    "pl": "plural",
    "sg": "singular",
    "locative": "locative",
    "genitive": "genitive",
    "dative": "dative",
    "accusative": "accusative",
    "instrumental": "instrumental",
    "vocative": "vocative",
    "nominative": "nominative",
    "cvb-adv-part-past": "past participle",
    "cvb-adv-part-absolute": "converb",
    "causative-voice": "causative",
    "root": "root",
}

_TAG_RE = re.compile(r"<([^>]+)>")

# Atomic chillu characters (U+0D7A–U+0D7F) → base + virama, which mlmorph expects.
_CHILLU = str.maketrans({"ൺ": "ണ്", "ൻ": "ന്", "ർ": "ര്", "ൽ": "ല്", "ൾ": "ള്", "ൿ": "ക്"})


def _get_analyser():
    """Return the module-level mlmorph Analyser singleton, creating it on first call."""
    global _analyser
    if _analyser is None:
        _analyser = Analyser()
    return _analyser


@lru_cache(maxsize=4096)
def analyse_word(word: str) -> list[str] | None:
    """Return human-readable morphological labels for a Malayalam word, or None."""
    try:
        results = _get_analyser().analyse(word.translate(_CHILLU))
    except Exception:
        return None
    if not results:
        return None

    labels: list[str] = []
    seen: set[str] = set()

    for analysis, _ in results:
        tags = _TAG_RE.findall(analysis)
        if not tags:
            continue

        raw_root = analysis.split("<")[0].strip()
        pos_label = _POS.get(tags[0]) or tags[0]

        feature_tags = tags[1:]
        features = [_FEATURES[t] for t in feature_tags if t in _FEATURES]
        root_differs = bool(raw_root and raw_root != word)

        if not features:
            label = f"{pos_label}, related to {raw_root}" if root_differs else pos_label
        else:
            main = features[0]
            label = f"{main} {pos_label} of {raw_root}" if root_differs else f"{main} {pos_label}"

        if label not in seen:
            seen.add(label)
            labels.append(label)

    return labels if labels else None
