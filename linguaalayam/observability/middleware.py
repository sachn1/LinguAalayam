"""ASGI middleware that records one request_log row per inbound HTTP request."""

import logging
import re
import time

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from linguaalayam.api.dependencies import get_session_factory
from linguaalayam.database.session import get_session
from linguaalayam.observability.http import client_ip
from linguaalayam.observability.queries import log_request

log = logging.getLogger(__name__)

# Coarse route classification for analytics — path prefix -> route_type label.
# More specific prefixes (e.g. "/mcp/setup") must precede broader ones (e.g. "/mcp")
# since the first match wins — otherwise a human viewing the setup page would be
# counted the same as an AI assistant's actual MCP protocol traffic.
_ROUTE_TYPES: list[tuple[str, str]] = [
    ("/search", "web_search"),
    ("/lookup/exact", "lookup_exact"),
    ("/lookup/fuzzy", "lookup_fuzzy"),
    ("/lookup/semantic", "lookup_semantic"),
    ("/mcp/setup", "mcp_setup_page"),
    ("/mcp", "mcp"),
    ("/health", "health"),
    ("/docs", "api_docs"),
    ("/openapi.json", "api_docs"),
]

# Paths never worth a request_log row from the generic middleware: the analytics
# dashboard's own polling (logging it would create a feedback loop where watching
# traffic generates traffic), the liveness probe (infra noise, never real
# user/bot activity), and /track/click (its handler logs its own row with a
# label-specific route_type — see observability/router.py — so double-logging
# it here under a generic classification would be redundant and wrong).
_EXCLUDED_PREFIXES = ("/admin", "/health", "/track/click")

# Known crawler/bot user-agent substrings (case-insensitive). Not authoritative —
# Cloudflare's real bot score is an Enterprise-only feature — but enough to separate
# obvious automated traffic (search engine crawlers, uptime pingers, HTTP libraries)
# from browser-driven use when eyeballing the request_log table.
_BOT_UA_PATTERN = re.compile(
    r"bot|crawl|spider|slurp|curl|wget|python-requests|httpx|axios|go-http-client|"
    r"scrapy|headless|monitor|pingdom|uptimerobot|facebookexternalhit",
    re.IGNORECASE,
)


def classify_route(path: str) -> str:
    """Map a request path to a coarse route_type label for analytics."""
    for prefix, route_type in _ROUTE_TYPES:
        if path.startswith(prefix):
            return route_type
    return "other"


def looks_like_bot(user_agent: str | None) -> bool:
    """Heuristic guess that a request is automated, based on its User-Agent string."""
    return bool(user_agent) and bool(_BOT_UA_PATTERN.search(user_agent))


class RequestLoggingMiddleware:
    """Raw ASGI middleware that records one ``request_log`` row per HTTP request.

    Implemented as pure ASGI (rather than ``BaseHTTPMiddleware``) because the
    latter buffers the whole response, which breaks the MCP sub-app's
    streamable-HTTP (SSE) responses mounted at ``/mcp``.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"].startswith(_EXCLUDED_PREFIXES):
            await self.app(scope, receive, send)
            return

        start = time.monotonic()
        status_holder: dict[str, int] = {}

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            self._record(scope, status_holder.get("status", 0), (time.monotonic() - start) * 1000)

    @staticmethod
    def _record(scope: Scope, status_code: int, duration_ms: float) -> None:
        """Best-effort insert of one analytics row — never let logging break a request."""
        try:
            request = Request(scope)
            path = request.url.path
            session_factory = get_session_factory()
            with get_session(session_factory) as session:
                log_request(
                    session,
                    method=request.method,
                    path=path,
                    route_type=classify_route(path),
                    query=request.query_params.get("query"),
                    status_code=status_code,
                    duration_ms=duration_ms,
                    ip=client_ip(request),
                    country=request.headers.get("cf-ipcountry"),
                    user_agent=request.headers.get("user-agent"),
                    is_bot=looks_like_bot(request.headers.get("user-agent")),
                )
        except Exception:  # pragma: no cover — logging must never break a request
            log.warning("Failed to record request_log entry", exc_info=True)
