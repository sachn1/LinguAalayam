"""Tests for rag/tools.py — DictionaryTools and merge_candidates."""

from unittest.mock import MagicMock, patch

from linguaalayam.rag.tools import DictionaryTools, merge_candidates


def _candidate(headword: str, source: str = "olam_enml", match_type: str = "exact") -> dict:
    """Build a minimal candidate dict for the given headword."""
    return {
        "headword": headword,
        "source": source,
        "entry_type": "OlamEntry",
        "embed_text": f"word: {headword}",
        "data": {},
        "match_type": match_type,
        "score": 1.0,
    }


class TestMergeCandidates:
    """merge_candidates deduplication and priority ordering."""

    def test_deduplicates_by_source_and_headword(self):
        """The same (source, headword) from two lists should produce one entry."""
        a = [_candidate("run", match_type="exact")]
        b = [_candidate("run", match_type="fuzzy")]
        merged = merge_candidates([a, b])
        assert len(merged) == 1
        assert merged[0]["match_type"] == "exact"  # first list wins

    def test_preserves_distinct_entries(self):
        """Different headwords should all appear in the merged list."""
        a = [_candidate("run")]
        b = [_candidate("walk")]
        merged = merge_candidates([a, b])
        assert len(merged) == 2

    def test_empty_lists(self):
        """Two empty lists should produce an empty merged list."""
        assert merge_candidates([[], []]) == []

    def test_single_list(self):
        """A single-element input should pass through unchanged."""
        a = [_candidate("run"), _candidate("walk")]
        merged = merge_candidates([a])
        assert len(merged) == 2

    def test_priority_order(self):
        """Earlier list entries should appear before later-list entries in output."""
        a = [_candidate("run", match_type="exact")]
        b = [_candidate("run", match_type="semantic")]
        c = [_candidate("fly", match_type="semantic")]
        merged = merge_candidates([a, b, c])
        headwords = [r["headword"] for r in merged]
        assert headwords.index("run") < headwords.index("fly")


class TestDictionaryTools:
    """DictionaryTools exact, fuzzy, and semantic lookup wrappers."""

    def _make_tools(self):
        """Build a DictionaryTools with mock session factory and embedder."""
        session_factory = MagicMock()
        embedding_service = MagicMock()
        embedding_service.encode_query.return_value = [0.1, 0.2, 0.3, 0.4]
        return (
            DictionaryTools(session_factory, embedding_service),
            session_factory,
            embedding_service,
        )

    def _mock_session_ctx(self):
        """Build a mock async-compatible session context manager."""
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=MagicMock())
        ctx.__exit__ = MagicMock(return_value=False)
        return ctx

    def test_exact_lookup_returns_results(self):
        """exact_lookup should serialise ORM rows into result dicts."""
        tools, sf, _ = self._make_tools()
        mock_entry = MagicMock()
        mock_entry.headword = "run"
        mock_entry.source = "olam_enml"
        mock_entry.entry_type = "OlamEntry"
        mock_entry.embed_text = "word: run"
        mock_entry.data = {}

        with (
            patch("linguaalayam.rag.tools.get_session", return_value=self._mock_session_ctx()),
            patch("linguaalayam.rag.tools.exact_search", return_value=[mock_entry]),
        ):
            results = tools.exact_lookup("run")

        assert len(results) == 1
        assert results[0]["headword"] == "run"
        assert results[0]["match_type"] == "exact"
        assert results[0]["score"] == 1.0

    def test_exact_lookup_empty(self):
        """exact_lookup should return an empty list on miss."""
        tools, _, _ = self._make_tools()
        with (
            patch("linguaalayam.rag.tools.get_session", return_value=self._mock_session_ctx()),
            patch("linguaalayam.rag.tools.exact_search", return_value=[]),
        ):
            results = tools.exact_lookup("xyzzy")
        assert results == []

    def test_fuzzy_lookup_returns_results(self):
        """fuzzy_lookup should return results with match_type='fuzzy'."""
        tools, _, _ = self._make_tools()
        mock_entry = MagicMock()
        mock_entry.headword = "run"
        mock_entry.source = "olam_enml"
        mock_entry.entry_type = "OlamEntry"
        mock_entry.embed_text = "word: run"
        mock_entry.data = {}

        with (
            patch("linguaalayam.rag.tools.get_session", return_value=self._mock_session_ctx()),
            patch("linguaalayam.rag.tools.fuzzy_search", return_value=[(mock_entry, 0.8)]),
        ):
            results = tools.fuzzy_lookup("runing")

        assert len(results) == 1
        assert results[0]["match_type"] == "fuzzy"
        assert results[0]["score"] == 0.8

    def test_semantic_lookup_encodes_query(self):
        """semantic_lookup should embed the query before calling similarity_search."""
        tools, _, embed_svc = self._make_tools()
        mock_entry = MagicMock()
        mock_entry.headword = "run"
        mock_entry.source = "olam_enml"
        mock_entry.entry_type = "OlamEntry"
        mock_entry.embed_text = "word: run"
        mock_entry.data = {}

        with (
            patch("linguaalayam.rag.tools.get_session", return_value=self._mock_session_ctx()),
            patch("linguaalayam.rag.tools.similarity_search", return_value=[(mock_entry, 0.9)]),
        ):
            results = tools.semantic_lookup("to move quickly on foot")

        embed_svc.encode_query.assert_called_once_with("to move quickly on foot")
        assert len(results) == 1
        assert results[0]["match_type"] == "semantic"

    def test_exact_lookup_passes_source(self):
        """Source filter should be forwarded to exact_search."""
        tools, _, _ = self._make_tools()
        with (
            patch("linguaalayam.rag.tools.get_session", return_value=self._mock_session_ctx()),
            patch("linguaalayam.rag.tools.exact_search", return_value=[]) as mock_es,
        ):
            tools.exact_lookup("run", source="olam_enml")
        mock_es.assert_called_once()
        _, kwargs = mock_es.call_args
        assert kwargs.get("source") == "olam_enml" or mock_es.call_args[0][2] == "olam_enml"

    def test_fuzzy_lookup_reclassifies_shared_lemma_as_lemma(self):
        """A fuzzy candidate that's a true inflection of the query becomes match_type='lemma'."""
        tools, _, _ = self._make_tools()
        mock_entry = MagicMock()
        mock_entry.headword = "നിന്ദിക്കുക"  # dictionary lemma the inflected query shares
        mock_entry.source = "datuk"
        mock_entry.entry_type = "DatukEntry"
        mock_entry.embed_text = "word: നിന്ദിക്കുക"
        mock_entry.data = {}

        with (
            patch("linguaalayam.rag.tools.get_session", return_value=self._mock_session_ctx()),
            patch("linguaalayam.rag.tools.fuzzy_search", return_value=[(mock_entry, 0.62)]),
        ):
            results = tools.fuzzy_lookup("നിന്ദിക്കുന്നു")  # present tense of the same verb

        assert len(results) == 1
        assert results[0]["match_type"] == "lemma"
        assert results[0]["score"] == 0.62  # real trigram score is preserved, not overwritten

    def test_fuzzy_lookup_english_self_match_is_not_reclassified_as_lemma(self):
        """Regression: querying an English word like 'run' must not get treated
        as a self-lemma match (mlmorph's foreign-word fallback used to echo
        'run' back as its own "root", trivially satisfying the relatedness
        check and wrongly suppressing every other genuine fuzzy candidate)."""
        tools, _, _ = self._make_tools()
        exact_self = MagicMock()
        exact_self.headword = "run"
        exact_self.source = "olam_enml"
        exact_self.entry_type = "OlamEntry"
        exact_self.embed_text = "word: run"
        exact_self.data = {}

        other = MagicMock()
        other.headword = "runner"
        other.source = "olam_enml"
        other.entry_type = "OlamEntry"
        other.embed_text = "word: runner"
        other.data = {}

        with (
            patch("linguaalayam.rag.tools.get_session", return_value=self._mock_session_ctx()),
            patch(
                "linguaalayam.rag.tools.fuzzy_search",
                return_value=[(exact_self, 1.0), (other, 0.5)],
            ),
        ):
            results = tools.fuzzy_lookup("run")

        assert [r["match_type"] for r in results] == ["fuzzy", "fuzzy"]

    def test_fuzzy_lookup_keeps_unrelated_spelling_matches_as_fuzzy(self):
        """A candidate that only looks similar (different mlmorph lemma) stays 'fuzzy'."""
        tools, _, _ = self._make_tools()
        mock_entry = MagicMock()
        mock_entry.headword = "നന്ദിക്കുക"  # "to thank" — spelling-adjacent, unrelated meaning
        mock_entry.source = "datuk"
        mock_entry.entry_type = "DatukEntry"
        mock_entry.embed_text = "word: നന്ദിക്കുക"
        mock_entry.data = {}

        with (
            patch("linguaalayam.rag.tools.get_session", return_value=self._mock_session_ctx()),
            patch("linguaalayam.rag.tools.fuzzy_search", return_value=[(mock_entry, 0.64)]),
        ):
            results = tools.fuzzy_lookup("നിന്ദിക്കുക")  # "to insult" — different root

        assert len(results) == 1
        assert results[0]["match_type"] == "fuzzy"

    def test_lemma_lookup_resolves_inflected_query_to_its_root(self):
        """lemma_lookup should look up the query's mlmorph root, not the query itself."""
        tools, _, _ = self._make_tools()
        mock_entry = MagicMock()
        mock_entry.headword = "നിന്ദിക്കുക"
        mock_entry.source = "datuk"
        mock_entry.entry_type = "DatukEntry"
        mock_entry.embed_text = "word: നിന്ദിക്കുക"
        mock_entry.data = {}

        with (
            patch("linguaalayam.rag.tools.get_session", return_value=self._mock_session_ctx()),
            patch("linguaalayam.rag.tools.exact_search", return_value=[mock_entry]) as mock_es,
        ):
            results = tools.lemma_lookup("നിന്ദിക്കുന്നു")

        mock_es.assert_called_once()
        assert mock_es.call_args[0][1] == "നിന്ദിക്കുക"  # looked up the lemma, not the query
        assert len(results) == 1
        assert results[0]["match_type"] == "lemma"
        assert results[0]["score"] == 1.0

    def test_lemma_lookup_empty_when_query_is_already_a_base_form(self):
        """lemma_lookup should no-op when mlmorph's root equals the query itself."""
        tools, _, _ = self._make_tools()
        with patch("linguaalayam.rag.tools.get_session", return_value=self._mock_session_ctx()):
            results = tools.lemma_lookup("നിന്ദിക്കുക")
        assert results == []

    def test_lemma_lookup_empty_when_unanalysable(self):
        """lemma_lookup should no-op for words mlmorph can't analyse (e.g. English)."""
        tools, _, _ = self._make_tools()
        with patch("linguaalayam.rag.tools.get_session", return_value=self._mock_session_ctx()):
            results = tools.lemma_lookup("xyzzy")
        assert results == []
