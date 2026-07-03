"""Varnam API client — Manglish (Latin script) to Malayalam transliteration.

Calls the public Varnam API (https://api.varnamproject.com) to convert
informal romanised Malayalam (Manglish) into ranked Malayalam candidates.

Security considerations:
- HTTPS with certificate verification enforced (never disabled).
- Response validated for structure and script before use.
- Strict timeout — never blocks the request cycle.
- User-Agent identifies the caller to the upstream service.
- No user data is logged; only the transliterated word is sent.
"""

import logging
import re

import httpx

log = logging.getLogger(__name__)

_BASE_URL = "https://api.varnamproject.com/tl/ml"
_TIMEOUT = httpx.Timeout(connect=3.0, read=4.0, write=None, pool=None)
_HEADERS = {"User-Agent": "linguaalayam/1.0 (https://linguaalayam.org)"}

# Malayalam Unicode block U+0D00–U+0D7F.
_ML_RE = re.compile(r"^[\u0D00-\u0D7F]+$")


def _is_malayalam(word: str) -> bool:
    """Return True if *word* contains only Malayalam script characters."""
    return bool(word) and bool(_ML_RE.match(word))


def manglish_to_malayalam(word: str) -> list[str]:
    """Return deduplicated, validated Malayalam candidates for a Manglish word.

    Calls the Varnam API and returns the ranked candidate list with:
    - duplicates removed (preserving rank order)
    - non-Malayalam tokens filtered out
    - empty list returned on any network or parsing error

    Parameters
    ----------
    word : str
        A single Manglish word (Latin script romanised Malayalam).

    Returns
    -------
    list[str]
        Ranked, deduplicated Malayalam candidates. Empty list if the API is
        unreachable, returns no results, or returns invalid content.
    """
    url = f"{_BASE_URL}/{word}"
    try:
        with httpx.Client(verify=True, timeout=_TIMEOUT, headers=_HEADERS) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.TimeoutException:
        log.warning("Varnam API timed out for %r", word)
        return []
    except httpx.HTTPStatusError as exc:
        log.warning("Varnam API returned HTTP %s for %r", exc.response.status_code, word)
        return []
    except httpx.RequestError as exc:
        log.warning("Varnam API request failed for %r: %s", word, exc)
        return []

    try:
        data = response.json()
    except Exception:
        log.warning("Varnam API returned non-JSON response for %r", word)
        return []

    if not isinstance(data, dict) or not data.get("success"):
        log.debug("Varnam API unsuccessful for %r: %s", word, data.get("error", "unknown"))
        return []

    raw: object = data.get("result")
    if not isinstance(raw, list):
        log.warning("Varnam API result is not a list for %r", word)
        return []

    # Deduplicate preserving rank order; filter non-Malayalam tokens.
    seen: set[str] = set()
    candidates: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        item = item.strip()
        if item and _is_malayalam(item) and item not in seen:
            seen.add(item)
            candidates.append(item)

    return candidates