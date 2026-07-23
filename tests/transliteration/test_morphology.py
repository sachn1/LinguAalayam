"""Tests for transliteration/morphology.py — mlmorph-backed analysis and lemma lookup."""

from linguaalayam.transliteration.morphology import analyse_word, get_lemma


class TestGetLemma:
    """get_lemma resolves inflected Malayalam surface forms to their dictionary root."""

    def test_inflected_verb_resolves_to_its_root(self):
        assert get_lemma("നിന്ദിക്കുന്നു") == "നിന്ദിക്കുക"

    def test_base_form_resolves_to_itself(self):
        assert get_lemma("നിന്ദിക്കുക") == "നിന്ദിക്കുക"

    def test_unrelated_similarly_spelled_word_has_a_different_lemma(self):
        """നന്ദിക്കുക ("to thank") must not resolve to the same root as
        നിന്ദിക്കുക ("to insult") despite the near-identical spelling — this is
        the whole basis for distinguishing genuine inflections from
        coincidental trigram matches in rag/tools.py."""
        assert get_lemma("നന്ദിക്കുക") != get_lemma("നിന്ദിക്കുക")

    def test_english_word_returns_none_not_itself(self):
        """Regression: mlmorph tags unsegmentable input as a foreign word
        (`run<fw>`), echoing the word back as its own "root" — that fallback
        must not be surfaced as a real lemma, or every English/OOV query
        would look like a trivial self-lemma match (see fuzzy_lookup in
        rag/tools.py, which would otherwise treat any identically-spelled
        fuzzy candidate as a confirmed relation and suppress everything else)."""
        assert get_lemma("run") is None
        assert get_lemma("house") is None

    def test_unanalysable_gibberish_returns_none(self):
        assert get_lemma("xyzzy") is None


class TestAnalyseWord:
    """analyse_word still returns human-readable labels for real Malayalam words."""

    def test_inflected_verb_has_a_label(self):
        labels = analyse_word("നിന്ദിക്കുന്നു")
        assert labels
        assert any("നിന്ദിക്കുക" in label for label in labels)
