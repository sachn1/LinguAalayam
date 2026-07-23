"""Remote MCP server — mounted into the FastAPI app at /mcp.

Shares DictionaryTools with the REST API (no second DB connection or model load).
Clients connect via URL: https://linguaalayam.org/mcp — no local install required.

OAuth 2.0 (RFC 7591 dynamic registration + PKCE) is enabled so Claude.ai's browser
MCP connector can authenticate. The provider is a passthrough — it auto-approves
every authorization request because LinguAalayam is a public dictionary service with
no user accounts. Tokens are in-memory; a server restart invalidates them and clients
re-authorize automatically.
"""

import logging
import os

from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.requests import Request

from linguaalayam.api.dependencies import get_tools
from linguaalayam.api.oauth import PassthroughOAuthProvider
from linguaalayam.mcp.shared import format_results as _format
from linguaalayam.observability import log_feature_event
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings

log = logging.getLogger(__name__)

_ISSUER_URL = os.environ.get("MCP_ISSUER_URL", "http://localhost:8000/mcp")

_oauth_provider = PassthroughOAuthProvider()

mcp = FastMCP(
    "linguaalayam",
    # Mount point is /mcp; path '/' means the MCP endpoint is at /mcp (not /mcp/mcp).
    streamable_http_path="/",
    # DNS rebinding protection defaults to localhost-only when host="127.0.0.1".
    # Disable it here — we run behind nginx which handles host/origin security.
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    instructions=(
        "Malayalam lexical knowledge base built on the Olam, Datuk, and Ekkurup corpora. "
        "Use exact_lookup first for a known word spelling. "
        "Use fuzzy_lookup for approximate matches or typos. "
        "Use semantic_lookup for meaning-based queries or when the exact headword is unknown."
    ),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(_ISSUER_URL),
        service_documentation_url=AnyHttpUrl("https://linguaalayam.org/mcp/setup"),
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=["dictionary"],
            default_scopes=["dictionary"],
        ),
        revocation_options=RevocationOptions(enabled=True),
        required_scopes=["dictionary"],
        resource_server_url=None,
    ),
    auth_server_provider=_oauth_provider,
)


def _log_tool_call(ctx: Context, tool: str, query: str) -> None:
    """Best-effort per-tool MCP usage logging — never let it break a tool call.

    Streamable-HTTP transport (used at /mcp) exposes the underlying Starlette
    Request via ctx.request_context.request, giving IP/UA/country the same
    way any other route gets it — stdio transport (linguaalayam/mcp/server.py,
    `poetry run mcp-server`) has no such request, so this is a no-op there.

    ctx.request_context is a property that raises (not returns None) when
    accessed outside an active request — wrap the whole thing, not just the
    log call, or that raise propagates straight out of the tool.
    """
    try:
        request = ctx.request_context.request if ctx.request_context else None
        if isinstance(request, Request):
            log_feature_event(f"mcp_{tool}", request, query=query)
    except Exception:  # pragma: no cover — logging must never break a tool call
        log.warning("Failed to record MCP tool-call event for %r", tool, exc_info=True)


@mcp.resource("dictionary://{headword}")
def get_entry(headword: str, ctx: Context) -> str:
    """Browse a dictionary entry by URI (e.g. dictionary://run)."""
    _log_tool_call(ctx, "resource", headword)
    results = get_tools().exact_lookup(headword)
    return _format(results, headword, "exact")


@mcp.tool()
def exact_lookup(word: str, ctx: Context, source: str | None = None) -> str:
    """Look up a word by exact headword match (case-insensitive).

    Args:
        word: The word to look up (English or Malayalam).
        source: Optional corpus filter (e.g. "olam_enml"). Searches all corpora if omitted.
    """
    _log_tool_call(ctx, "exact_lookup", word)
    results = get_tools().exact_lookup(word, source=source)
    return _format(results, word, "exact")


@mcp.tool()
def fuzzy_lookup(
    query: str,
    ctx: Context,
    threshold: float = 0.3,
    top_k: int = 10,
    source: str | None = None,
) -> str:
    """Search for words by approximate headword similarity (trigram).

    Args:
        query: The word or partial word to search for.
        threshold: Minimum trigram similarity score (0–1). Default 0.3.
        top_k: Maximum number of results to return. Default 10.
        source: Optional corpus filter. Searches all corpora if omitted.
    """
    _log_tool_call(ctx, "fuzzy_lookup", query)
    results = get_tools().fuzzy_lookup(query, source=source, threshold=threshold, top_k=top_k)
    return _format(results, query, "fuzzy")


@mcp.tool()
def semantic_lookup(
    query: str,
    ctx: Context,
    top_k: int = 5,
    source: str | None = None,
) -> str:
    """Search for words by meaning similarity using sentence embeddings.

    Args:
        query: A word, phrase, or description of the meaning to search for.
        top_k: Number of top results to return. Default 5.
        source: Optional corpus filter. Searches all corpora if omitted.
    """
    _log_tool_call(ctx, "semantic_lookup", query)
    results = get_tools().semantic_lookup(query, top_k=top_k, source=source)
    return _format(results, query, "semantic")


_mcp_app: Starlette | None = None


def get_mcp_app() -> Starlette:
    """Return the MCP Starlette sub-app singleton, creating it on first call."""
    global _mcp_app
    if _mcp_app is None:
        _mcp_app = mcp.streamable_http_app()
    return _mcp_app
