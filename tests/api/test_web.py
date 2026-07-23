"""Tests for HTMX web routes and static locale bundles."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from linguaalayam.api.app import app
from linguaalayam.translation.base import TranslationResult

_LOCALES = Path(__file__).resolve().parents[2] / "linguaalayam/static/locales"


def _passthrough_translation(text: str, source_lang: str = "en-US") -> TranslationResult:
    """Stub translator that returns the input unchanged (no translation needed)."""
    iso = source_lang.split("-")[0].lower()
    return TranslationResult(text=text, source_lang=iso, was_translated=False)


def _result(headword: str = "run", source: str = "olam_enml", match_type: str = "fuzzy") -> dict:
    """Build a minimal result dict shaped like DictionaryTools' _to_result output."""
    return {
        "headword": headword,
        "source": source,
        "entry_type": "OlamEntry",
        "embed_text": "",
        "data": {"definitions": [("v", "ഓടുക")]},
        "match_type": match_type,
        "score": 1.0,
    }


@pytest.fixture()
def mock_tools():
    t = MagicMock()
    t.exact_lookup.return_value = []
    t.fuzzy_lookup.return_value = []
    t.lemma_lookup.return_value = []
    t.semantic_lookup.return_value = []
    t.ml_headword_set.return_value = frozenset()
    return t


@pytest.fixture()
def mock_translator():
    t = MagicMock()
    t.translate.side_effect = _passthrough_translation
    return t


@pytest.fixture()
def client(mock_tools, mock_translator):
    with (
        patch("linguaalayam.api.web.get_tools", return_value=mock_tools),
        patch("linguaalayam.api.web.get_translator", return_value=mock_translator),
    ):
        yield TestClient(app, raise_server_exceptions=True)


# ── route smoke tests ──────────────────────────────────────────────────────────


def test_index_returns_200(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "lingu" in r.text


def test_search_empty_query(client, mock_tools):
    """Regression: an empty query used to raise UnboundLocalError on `tools`
    (only assigned inside `if q:`, but used unconditionally for ml_headword_set())."""
    r = client.get("/search")
    assert r.status_code == 200
    mock_tools.ml_headword_set.assert_called_once()


def test_search_single_word_uses_fuzzy(client, mock_tools):
    mock_tools.fuzzy_lookup.return_value = [_result()]  # results found — no fallback
    r = client.get("/search?query=run")
    assert r.status_code == 200
    mock_tools.fuzzy_lookup.assert_called_once()
    mock_tools.semantic_lookup.assert_not_called()


def test_search_no_results_shows_empty_state(client):
    r = client.get("/search?query=xyzzy_nonexistent")
    assert r.status_code == 200
    assert "No results" in r.text


# ── lemma-match suppression of coincidental spelling matches ───────────────────


def test_search_lemma_hit_suppresses_unrelated_fuzzy_matches(client, mock_tools):
    """A lemma_lookup hit is positive evidence for the query's root — once it
    exists, plain-fuzzy candidates (confirmed unrelated, not just lower-scoring)
    should be dropped rather than shown alongside it."""
    mock_tools.lemma_lookup.return_value = [_result(headword="നിന്ദിക്കുക", match_type="lemma")]
    mock_tools.fuzzy_lookup.return_value = [
        _result(headword="നന്ദിക്കുക", source="datuk", match_type="fuzzy"),
    ]
    r = client.get("/search?query=നിന്ദിക്കുന്നു")
    assert r.status_code == 200
    assert "നിന്ദിക്കുക" in r.text
    assert "നന്ദിക്കുക" not in r.text


def test_search_reclassified_lemma_fuzzy_hit_suppresses_other_fuzzy_matches(client, mock_tools):
    """fuzzy_lookup itself may reclassify a candidate as match_type='lemma' (see
    DictionaryTools.fuzzy_lookup) — that alone should also trigger suppression
    of the remaining plain-fuzzy candidates, with no lemma_lookup hit needed."""
    mock_tools.fuzzy_lookup.return_value = [
        _result(headword="നിന്ദിക്കുന്നു", source="datuk", match_type="lemma"),
        _result(headword="നിനാദിക്കുക", source="datuk", match_type="fuzzy"),
    ]
    r = client.get("/search?query=നിന്ദിക്കുക")
    assert r.status_code == 200
    assert "നിന്ദിക്കുന്നു" in r.text
    assert "നിനാദിക്കുക" not in r.text


def test_search_no_lemma_signal_keeps_all_fuzzy_matches(client, mock_tools):
    """With no lemma match anywhere (the common case — most queries are already
    base forms or aren't Malayalam at all), plain-fuzzy results are unaffected."""
    mock_tools.fuzzy_lookup.return_value = [
        _result(headword="run", match_type="fuzzy"),
        _result(headword="ran", source="datuk", match_type="fuzzy"),
    ]
    r = client.get("/search?query=run")
    assert r.status_code == 200
    assert "run" in r.text
    assert "ran" in r.text


# ── semantic fallback ─────────────────────────────────────────────────────────


def test_search_multiword_routes_to_semantic(client, mock_tools):
    """Multi-word queries bypass trigram and go straight to semantic."""
    r = client.get("/search?query=ഒരു+ജലസ്ഥലം")
    assert r.status_code == 200
    mock_tools.fuzzy_lookup.assert_not_called()
    mock_tools.semantic_lookup.assert_called_once()


def test_search_no_fuzzy_results_falls_back_to_semantic(client, mock_tools):
    """Single-word query with no fuzzy results falls back to semantic."""
    r = client.get("/search?query=xyzzy")
    assert r.status_code == 200
    mock_tools.semantic_lookup.assert_called()


# ── manglish / varnam fallback ────────────────────────────────────────────────


def test_search_latin_no_results_tries_varnam(client, mock_tools):
    """A Latin-script query with no fuzzy/semantic hits should try Varnam candidates."""
    with patch(
        "linguaalayam.transliteration.varnam.manglish_to_malayalam",
        return_value=["ഓടുക"],
    ) as mock_varnam:
        r = client.get("/search?query=oduka")
    assert r.status_code == 200
    mock_varnam.assert_called_once_with("oduka")


def test_search_varnam_success_sets_headword(client, mock_tools):
    """When Varnam returns a candidate that exists (exact/lemma), headword should update to it."""
    mock_tools.exact_lookup.return_value = [
        _result(headword="ഓടുക", source="datuk", match_type="exact")
    ]
    with patch(
        "linguaalayam.transliteration.varnam.manglish_to_malayalam",
        return_value=["ഓടുക"],
    ):
        r = client.get("/search?query=oduka")
    assert r.status_code == 200
    assert "ഓടുക" in r.text


def test_search_varnam_unavailable_falls_back_to_local_schemes(client, mock_tools):
    """If Varnam returns no candidates, fall back to local roman_to_malayalam_candidates."""
    with (
        patch("linguaalayam.transliteration.varnam.manglish_to_malayalam", return_value=[]),
        patch(
            "linguaalayam.api.web.roman_to_malayalam_candidates",
            return_value=["ഓടുക"],
        ) as mock_local,
    ):
        r = client.get("/search?query=oduka")
    assert r.status_code == 200
    mock_local.assert_called_once_with("oduka")


def test_search_manglish_fallback_skipped_when_translated(client, mock_tools, mock_translator):
    """A translated query should skip the Manglish fallback — it's real English, not Manglish."""
    mock_translator.translate.side_effect = lambda text, source_lang="en-US": TranslationResult(
        text="run", source_lang="de", was_translated=True
    )
    with patch("linguaalayam.transliteration.varnam.manglish_to_malayalam") as mock_varnam:
        r = client.get("/search?query=laufen&lang=de-DE")
    assert r.status_code == 200
    mock_varnam.assert_not_called()


# ── source mapping ────────────────────────────────────────────────────────────


def test_search_ml_ml_source_maps_to_list(client, mock_tools):
    """source=ml_ml in the UI should query both datuk and sayahna corpora."""
    mock_tools.fuzzy_lookup.return_value = [_result(source="datuk")]
    r = client.get("/search?query=run&source=ml_ml")
    assert r.status_code == 200
    _, kwargs = mock_tools.fuzzy_lookup.call_args
    assert kwargs.get("source") == ["datuk", "sayahna"]


def test_search_olam_source_passes_string(client, mock_tools):
    """Non-ml_ml source values should be forwarded as a plain string."""
    mock_tools.fuzzy_lookup.return_value = [_result()]
    r = client.get("/search?query=run&source=olam_enml")
    assert r.status_code == 200
    _, kwargs = mock_tools.fuzzy_lookup.call_args
    assert kwargs.get("source") == "olam_enml"


def test_search_empty_source_passes_none(client, mock_tools):
    """An empty source param should forward None (search all corpora)."""
    mock_tools.fuzzy_lookup.return_value = [_result()]
    r = client.get("/search?query=run&source=")
    assert r.status_code == 200
    _, kwargs = mock_tools.fuzzy_lookup.call_args
    assert kwargs.get("source") is None


# ── language parameter ─────────────────────────────────────────────────────────


def test_search_lang_param_accepted(client, mock_translator):
    """lang parameter should be accepted and forwarded to the translator."""
    r = client.get("/search?query=laufen&lang=de-DE")
    assert r.status_code == 200
    mock_translator.translate.assert_called_once_with("laufen", source_lang="de-DE")


def test_search_default_lang_is_en(client, mock_translator):
    """Omitting lang should default to en-US and pass it to the translator."""
    r = client.get("/search?query=run")
    assert r.status_code == 200
    _, kwargs = mock_translator.translate.call_args
    assert kwargs.get("source_lang") == "en-US"


# ── locale bundle tests ────────────────────────────────────────────────────────


def test_locale_files_exist():
    assert (_LOCALES / "en.json").exists()
    assert (_LOCALES / "ml.json").exists()


def test_locale_key_parity():
    en = json.loads((_LOCALES / "en.json").read_text())
    ml = json.loads((_LOCALES / "ml.json").read_text())
    diff = set(en.keys()) ^ set(ml.keys())
    assert not diff, f"locale key mismatch: {diff}"


def test_locale_no_empty_values():
    for name in ("en.json", "ml.json"):
        data = json.loads((_LOCALES / name).read_text())
        empty = [k for k, v in data.items() if not str(v).strip()]
        assert not empty, f"{name} has empty values: {empty}"


def test_locale_json_valid():
    for name in ("en.json", "ml.json"):
        content = (_LOCALES / name).read_text()
        json.loads(content)  # raises if invalid
