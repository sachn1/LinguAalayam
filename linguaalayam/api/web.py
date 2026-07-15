"""HTMX web UI routes — search page served as Jinja2 templates."""

import importlib.metadata
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from omegaconf import OmegaConf

from linguaalayam.api.dependencies import get_tools, get_translator
from linguaalayam.llm.adapters.anthropic import AnthropicAdapter
from linguaalayam.llm.adapters.nollm import NoLLMAdapter
from linguaalayam.llm.adapters.openai import OpenAIAdapter
from linguaalayam.rag.pipeline import _SYNTHESIS_SYSTEM, _SYNTHESIS_TEMPLATE, _format_entries
from linguaalayam.rag.query_understanding import understand_query
from linguaalayam.transliteration import (
    analyse_word,
    is_latin_script,
    malayalam_to_roman,
    roman_to_malayalam_candidates,
)

log = logging.getLogger(__name__)

_NO_LLM = NoLLMAdapter()
_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
_TEMPLATES.env.filters["romanise_ml"] = malayalam_to_roman
_TEMPLATES.env.globals["app_version"] = importlib.metadata.version("linguaalayam")


def _group_definitions(
    definitions: list[tuple[str | None, str]],
) -> list[tuple[str | None, list[str]]]:
    """Group a flat list of (pos, text) pairs into (pos, [text, ...]) groups.

    Preserves the first-seen order of POS tags while merging all definitions
    that share the same POS into a single list.

    Parameters
    ----------
    definitions : list[tuple[str | None, str]]
        Flat list of ``(part-of-speech, definition-text)`` pairs as stored in the DB.

    Returns
    -------
    list[tuple[str | None, list[str]]]
        Ordered list of ``(pos, [definitions])`` groups, one per unique POS.
    """
    seen: dict[str | None, list[str]] = {}
    order: list[str | None] = []
    for pos, text in definitions:
        if pos not in seen:
            seen[pos] = []
            order.append(pos)
        seen[pos].append(text)
    return [(pos, seen[pos]) for pos in order]


_TEMPLATES.env.filters["group_definitions"] = _group_definitions

router = APIRouter(include_in_schema=False)


def _make_llm(provider: str, key: str):
    """Instantiate an LLM adapter from a user-supplied key."""
    if provider == "openai":
        return OpenAIAdapter(
            OmegaConf.create({"api_key": key, "model": "gpt-4o-mini", "max_tokens": 512})
        )
    return AnthropicAdapter(
        OmegaConf.create({"api_key": key, "model": "claude-haiku-4-5-20251001", "max_tokens": 512})
    )


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    """Serve the main search page.

    Parameters
    ----------
    request : Request
        The incoming HTTP request.

    Returns
    -------
    HTMLResponse
        The rendered main search page.
    """
    return _TEMPLATES.TemplateResponse(request, "index.html")


@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request) -> HTMLResponse:
    """Serve the settings page.

    Parameters
    ----------
    request : Request
        The incoming HTTP request.

    Returns
    -------
    HTMLResponse
        The rendered settings page.
    """
    return _TEMPLATES.TemplateResponse(request, "settings.html")


@router.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request) -> HTMLResponse:
    """Serve the privacy page.

    Parameters
    ----------
    request : Request
        The incoming HTTP request.

    Returns
    -------
    HTMLResponse
        The rendered privacy page.
    """
    return _TEMPLATES.TemplateResponse(request, "privacy.html")


@router.get("/mcp/setup", response_class=HTMLResponse)
def mcp_setup(request: Request) -> HTMLResponse:
    """Serve the MCP setup page.

    Parameters
    ----------
    request : Request
        The incoming HTTP request.

    Returns
    -------
    HTMLResponse
        The rendered MCP setup page.
    """
    return _TEMPLATES.TemplateResponse(request, "mcp_setup.html")


@router.get("/mcp/setup/ping", response_class=HTMLResponse)
def mcp_ping() -> HTMLResponse:
    """Check the server's reachability.

    Parameters
    ----------
    request : Request
        The incoming HTTP request.

    Returns
    -------
    HTMLResponse
        The server's reachability status.
    """
    try:
        get_tools()
        return HTMLResponse('<span class="ping-ok">✓ Server is reachable</span>')
    except Exception:
        return HTMLResponse(
            '<span class="ping-err">✗ Server error — try again</span>', status_code=503
        )


@router.get("/search", response_class=HTMLResponse)
def search(
    request: Request,
    query: Annotated[str, Query()] = "",
    source: Annotated[str, Query()] = "",
    top_k: Annotated[int, Query()] = 10,
    lang: Annotated[str, Query()] = "en-US",
):
    """Handle a dictionary search request and return an HTMX partial or full results page.

    Parameters
    ----------
    request : Request
        The incoming HTTP request; headers ``X-Romanise``, ``X-LLM-Key``, and
        ``X-LLM-Provider`` are read for optional features.
    query : str, optional
        Search term (English, Malayalam, or Manglish).
    source : str, optional
        Corpus filter; ``"ml_ml"`` expands to both ``datuk`` and ``sayahna``.
    top_k : int, optional
        Maximum number of results to return; default ``10``.
    lang : str, optional
        BCP-47 language code for the query (used for translation pre-processing);
        default ``"en-US"``.

    Returns
    -------
    HTMLResponse
        HTMX partial ``results.html`` fragment or the full results page.
    """
    results = []
    answer: str | None = None
    varnam_used = False
    q = query.strip()
    _src = source.strip() or None
    # Expand logical source values to actual corpus names.
    # "ml_ml" = all Malayalam→Malayalam corpora; no value = search all.
    _EXPAND: dict[str, list[str]] = {
        "ml_ml": ["datuk", "sayahna"],
    }
    src: str | list[str] | None = _EXPAND.get(_src, _src) if _src else None
    romanise = request.headers.get("X-Romanise", "").strip() == "1"

    translation = get_translator().translate(q, source_lang=lang) if q else None
    q_en = translation.text if translation else q  # English (or original if EN/ML)

    tools = get_tools()
    headword = q_en
    if q:
        headword = understand_query(q_en, llm=_NO_LLM).headword or q_en

        # Always fuzzy — pg_trgm scores exact matches at 1.0 so they surface first.
        # Multi-word queries fall through to semantic for phrase/description retrieval.
        if " " in headword:
            results = tools.semantic_lookup(q_en, top_k=top_k, source=src)
        else:
            results = tools.fuzzy_lookup(headword, source=src, top_k=top_k)

        # Manglish fallback: Latin query with no results → try Varnam API candidates.
        # Skip when translation already ran — the headword is real English, not Manglish.
        if (
            not results
            and is_latin_script(headword)
            and not (translation and translation.was_translated)
        ):
            from linguaalayam.transliteration.varnam import manglish_to_malayalam  # lazy import

            ml_candidates = manglish_to_malayalam(headword)

            # Fall back to local scheme-based candidates if Varnam is unavailable.
            if not ml_candidates:
                ml_candidates = roman_to_malayalam_candidates(headword)
            else:
                varnam_used = True

            for ml_candidate in ml_candidates:
                results = tools.fuzzy_lookup(ml_candidate, source=src, top_k=top_k)
                if results:
                    headword = ml_candidate
                    break

        # Semantic fallback for single-word queries that got no fuzzy results.
        if not results and " " not in headword:
            results = tools.semantic_lookup(q_en, top_k=top_k, source=src)

        llm_key = request.headers.get("X-LLM-Key", "").strip()
        if llm_key and results:
            try:
                provider = request.headers.get("X-LLM-Provider", "anthropic").lower()
                llm = _make_llm(provider, llm_key)
                entries_text = _format_entries(results[:top_k])
                content = _SYNTHESIS_TEMPLATE.format(query=q, entries=entries_text)
                answer = llm.complete(_SYNTHESIS_SYSTEM, content)
            except Exception:
                log.warning("LLM synthesis failed for %r", q, exc_info=True)

    # Analyse the search query itself (shown above results as query context).
    # Only meaningful for Malayalam — skip for other non-Latin scripts.
    query_morphology: str | None = None
    source_is_ml = translation is None or translation.source_lang == "ml"
    if q and source_is_ml and not is_latin_script(q):
        labels = analyse_word(q)
        if labels:
            query_morphology = " / ".join(labels)

    return _TEMPLATES.TemplateResponse(
        request,
        "partials/results.html",
        {
            "results": results,
            "query": q,
            "headword": headword,
            "answer": answer,
            "source_filter": src,
            "romanise": romanise,
            "query_morphology": query_morphology,
            "translation": translation,
            "headword_set": tools.ml_headword_set(),
            "varnam_used": varnam_used,
        },
    )
