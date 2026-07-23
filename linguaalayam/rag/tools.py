"""Standalone dictionary retrieval tools — exact, fuzzy, and semantic lookup.

Each method is self-contained with no LangGraph imports so it can be
used directly from LangGraph nodes today and exposed as MCP tools in v0.3.
"""

from sqlalchemy.orm import sessionmaker

from linguaalayam.database.queries import exact_search, fuzzy_search, similarity_search
from linguaalayam.database.session import get_session
from linguaalayam.embeddings.service import EmbeddingService
from linguaalayam.models.orm import DictionaryEntry
from linguaalayam.transliteration.morphology import get_lemma


def merge_candidates(lists: list[list[dict]]) -> list[dict]:
    """Merge results from multiple tools, deduplicating on (source, headword).

    Parameters
    ----------
    lists : list[list[dict]]
        Result lists ordered by priority (exact, fuzzy, semantic).
        Earlier lists win on duplicate ``(source, headword)`` keys.

    Returns
    -------
    list[dict]
        Deduplicated candidate list preserving priority order.
    """
    seen: set[tuple[str, str]] = set()
    merged = []
    for results in lists:
        for item in results:
            key = (item["source"], item["headword"])
            if key not in seen:
                seen.add(key)
                merged.append(item)
    return merged


def _to_result(entry: DictionaryEntry, match_type: str, score: float) -> dict:
    """Serialise a DictionaryEntry ORM row into the standard result dict."""
    return {
        "headword": entry.headword,
        "source": entry.source,
        "entry_type": entry.entry_type,
        "embed_text": entry.embed_text,
        "data": entry.data,
        "match_type": match_type,
        "score": score,
    }


class DictionaryTools:
    """Retrieval tools over the dictionary database.

    Holds references to the session factory and embedding service so
    each tool method takes only domain-level arguments — the shape
    MCP tool handlers expect.

    Parameters
    ----------
    session_factory : sessionmaker
        SQLAlchemy session factory for opening DB sessions.
    embedding_service : EmbeddingService
        Service used to encode queries for semantic lookup.
    """

    def __init__(
        self,
        session_factory: sessionmaker,
        embedding_service: EmbeddingService,
    ) -> None:
        self._session_factory = session_factory
        self._embedder = embedding_service
        self._ml_headword_set: frozenset[str] | None = None

    def ml_headword_set(self) -> frozenset[str]:
        """Return a cached frozenset of all Malayalam headwords (datuk + sayahna).

        Used by the results template to determine which definition tokens are
        clickable (i.e. exist as their own dictionary entry). Loaded once on
        first call and cached for the lifetime of the process.

        Returns
        -------
        frozenset[str]
            All headwords from ML→ML corpora.
        """
        if self._ml_headword_set is None:
            with get_session(self._session_factory) as session:
                rows = (
                    session.query(DictionaryEntry.headword)
                    .filter(DictionaryEntry.source.in_(["datuk", "sayahna"]))
                    .all()
                )
            self._ml_headword_set = frozenset(r.headword for r in rows)
        return self._ml_headword_set

    def exact_lookup(
        self,
        query: str,
        source: str | list[str] | None = None,
    ) -> list[dict]:
        """Return entries whose headword is a case-insensitive exact match for query.

        Parameters
        ----------
        query : str
            Headword to look up (case-insensitive).
        source : str | list[str] | None, optional
            Corpus filter; searches all corpora when ``None``.

        Returns
        -------
        list[dict]
            Matched entries with ``match_type="exact"`` and ``score=1.0``.
        """
        with get_session(self._session_factory) as session:
            results = exact_search(session, query, source=source)
        return [_to_result(r, "exact", 1.0) for r in results]

    def fuzzy_lookup(
        self,
        query: str,
        source: str | list[str] | None = None,
        threshold: float = 0.3,
        top_k: int = 10,
    ) -> list[dict]:
        """Return entries whose headword is trigram-similar to query (pg_trgm).

        Falls back to an ILIKE-based search when running against SQLite (tests).

        Parameters
        ----------
        query : str
            Word or partial word to match against headwords.
        source : str | list[str] | None, optional
            Corpus filter; searches all corpora when ``None``.
        threshold : float, optional
            Minimum pg_trgm similarity score (0–1); default ``0.3``.
        top_k : int, optional
            Maximum results to return; default ``10``.

        Returns
        -------
        list[dict]
            Matched entries with pg_trgm similarity as score. ``match_type`` is
            normally ``"fuzzy"``, but candidates that share a dictionary lemma
            with `query` (per mlmorph) are reclassified as ``"lemma"`` — e.g. a
            hit for നിന്ദിക്കുന്നു is a genuine inflection of നിന്ദിക്കുക, not a
            coincidental spelling match, even though pg_trgm alone can't tell
            those two cases apart.
        """
        query_lemma = get_lemma(query)
        with get_session(self._session_factory) as session:
            results = fuzzy_search(session, query, source=source, threshold=threshold, limit=top_k)

        out = []
        for entry, score in results:
            related = query_lemma is not None and (
                entry.headword == query_lemma or get_lemma(entry.headword) == query_lemma
            )
            out.append(_to_result(entry, "lemma" if related else "fuzzy", score))
        return out

    def lemma_lookup(
        self,
        query: str,
        source: str | list[str] | None = None,
    ) -> list[dict]:
        """Return the dictionary entry for query's lemma, if query is an inflected form.

        Analyses `query` with mlmorph to find its dictionary root (e.g. നിന്ദിക്കുന്നു
        → നിന്ദിക്കുക) and looks that root up directly. This catches inflections
        whose surface form is too different from the lemma for pg_trgm's trigram
        overlap to surface them among :meth:`fuzzy_lookup`'s top candidates at all.

        Parameters
        ----------
        query : str
            Word to look up; expected to be an inflected Malayalam surface form.
        source : str | list[str] | None, optional
            Corpus filter; searches all corpora when ``None``.

        Returns
        -------
        list[dict]
            Entries for query's lemma with ``match_type="lemma"`` and ``score=1.0``,
            or ``[]`` when query is already a base form or mlmorph can't analyse it.
        """
        lemma = get_lemma(query)
        if not lemma or lemma == query:
            return []
        with get_session(self._session_factory) as session:
            results = exact_search(session, lemma, source=source)
        return [_to_result(r, "lemma", 1.0) for r in results]

    def semantic_lookup(
        self,
        query: str,
        top_k: int = 5,
        source: str | list[str] | None = None,
    ) -> list[dict]:
        """Return entries ranked by cosine similarity of their embed_text to query.

        Parameters
        ----------
        query : str
            Natural-language query; embedded before the vector search.
        top_k : int, optional
            Number of top results to return; default ``5``.
        source : str | list[str] | None, optional
            Corpus filter; searches all corpora when ``None``.

        Returns
        -------
        list[dict]
            Top-k entries with ``match_type="semantic"`` and cosine similarity as score.
        """
        query_vector = self._embedder.encode_query(query)
        with get_session(self._session_factory) as session:
            results = similarity_search(session, query_vector, top_k=top_k, source=source)
        return [_to_result(r, "semantic", score) for r, score in results]
