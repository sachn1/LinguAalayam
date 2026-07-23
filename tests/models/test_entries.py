"""Tests for OlamEntry, DatukEntry, and SayahnaEntry dataclasses."""

from linguaalayam.models.entries import DatukEntry, OlamEntry, SayahnaEntry


class TestOlamEntry:
    """OlamEntry construction and embed_text generation."""

    def test_headword(self):
        """headword field should be stored as-is."""
        e = OlamEntry(headword="run", definitions=[("v", "ഓടുക")])
        assert e.headword == "run"

    def test_default_source(self):
        """Default source should be 'olam_enml'."""
        e = OlamEntry(headword="run", definitions=[("v", "ഓടുക")])
        assert e.source == "olam_enml"

    def test_embed_text_contains_headword(self):
        """embed_text should include the headword string."""
        e = OlamEntry(headword="run", definitions=[("v", "ഓടുക")])
        assert "run" in e.to_embed_text()

    def test_embed_text_contains_definition(self):
        """embed_text should include the Malayalam definition."""
        e = OlamEntry(headword="run", definitions=[("v", "ഓടുക")])
        assert "ഓടുക" in e.to_embed_text()

    def test_embed_text_groups_by_pos(self):
        """Multiple definitions should be grouped under their POS tag."""
        e = OlamEntry(headword="run", definitions=[("v", "ഓടുക"), ("v", "പായുക"), ("n", "ഓട്ടം")])
        text = e.to_embed_text()
        # Both verb definitions should appear under [v]
        assert "[v]" in text
        assert "[n]" in text

    def test_embed_text_none_pos_shown_as_general(self):
        """A None POS should render as [general] in embed_text."""
        e = OlamEntry(headword="A", definitions=[(None, "ഒരു")])
        assert "[general]" in e.to_embed_text()

    def test_embed_text_returns_string(self):
        """to_embed_text should always return a str."""
        e = OlamEntry(headword="run", definitions=[])
        assert isinstance(e.to_embed_text(), str)

    def test_morphology_always_none(self):
        """English headwords should never get mlmorph analysis."""
        e = OlamEntry(headword="run", definitions=[("v", "ഓടുക")])
        assert e.morphology is None


class TestDatukEntry:
    """DatukEntry construction and embed_text."""

    def test_default_source(self):
        """Default source should be 'datuk'."""
        e = DatukEntry(headword="ഓടുക", definitions=[("v", "വേഗത്തിൽ ചലിക്കുക")])
        assert e.source == "datuk"

    def test_embed_text_contains_headword(self):
        """embed_text should include the Malayalam headword."""
        e = DatukEntry(headword="ഓടുക", definitions=[("v", "വേഗത്തിൽ ചലിക്കുക")])
        assert "ഓടുക" in e.to_embed_text()

    def test_morphology_computed_at_construction(self):
        """A real Malayalam headword should get mlmorph analysis, not silently None.

        Regression test: _compute_morphology previously imported from the old
        linguaalayam.morphology path (removed when morphology.py moved under
        transliteration/), which made this always None via a swallowed ImportError.
        """
        e = DatukEntry(headword="ഓടുക", definitions=[("v", "വേഗത്തിൽ ചലിക്കുക")])
        assert e.morphology is not None
        assert len(e.morphology) > 0

    def test_morphology_uses_first_variant_for_comma_separated_headword(self):
        """Multi-variant headwords (e.g. 'foo, bar') should analyse only the first."""
        e = DatukEntry(headword="ഓടുക, പായുക", definitions=[("v", "വേഗത്തിൽ ചലിക്കുക")])
        assert e.morphology is not None


class TestSayahnaEntry:
    """SayahnaEntry construction and embed_text generation."""

    def test_default_source(self):
        """Default source should be 'sayahna'."""
        e = SayahnaEntry(headword="അംശം", definitions=[(None, "ഭാഗം")])
        assert e.source == "sayahna"

    def test_default_explanations_empty(self):
        """explanations should default to an empty list."""
        e = SayahnaEntry(headword="അംശം", definitions=[(None, "ഭാഗം")])
        assert e.explanations == []

    def test_embed_text_contains_headword(self):
        """embed_text should include the Malayalam headword."""
        e = SayahnaEntry(headword="അംശം", definitions=[(None, "ഭാഗം")])
        assert "അംശം" in e.to_embed_text()

    def test_embed_text_contains_definition(self):
        """embed_text should include the definition text."""
        e = SayahnaEntry(headword="അംശം", definitions=[(None, "ഭാഗം")])
        assert "ഭാഗം" in e.to_embed_text()

    def test_embed_text_with_pos(self):
        """embed_text should include POS label when present."""
        e = SayahnaEntry(headword="അംശജ", definitions=[("adj.", "അംശം കൊണ്ടു ജനിച്ച")])
        assert "[adj.]" in e.to_embed_text()

    def test_embed_text_none_pos_shown_as_general(self):
        """A None POS should render as [general] in embed_text."""
        e = SayahnaEntry(headword="അംശം", definitions=[(None, "ഭാഗം")])
        assert "[general]" in e.to_embed_text()

    def test_embed_text_includes_explanations(self):
        """embed_text should append explanations as notes."""
        e = SayahnaEntry(
            headword="അഋണി", definitions=[(None, "കടമില്ലാത്തവൻ")], explanations=["സ്ത്രീ: അനൃണിനി."]
        )
        text = e.to_embed_text()
        assert "notes:" in text
        assert "അനൃണിനി" in text

    def test_embed_text_no_notes_when_no_explanations(self):
        """embed_text should not include a notes line when explanations is empty."""
        e = SayahnaEntry(headword="അംശം", definitions=[(None, "ഭാഗം")])
        assert "notes:" not in e.to_embed_text()
