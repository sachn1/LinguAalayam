"""Feature-usage analytics events logged outside RequestLoggingMiddleware's generic
per-request classification — either because the "event" isn't its own HTTP request
(e.g. Varnam's manglish fallback, triggered inside /search's handling) or because it
needs a route_type the generic path-prefix classifier can't express (e.g. distinguishing
which button on /track/click was actually clicked).
"""

import logging

from starlette.requests import Request

from linguaalayam.api.dependencies import get_session_factory
from linguaalayam.database.session import get_session
from linguaalayam.observability.http import client_ip
from linguaalayam.observability.middleware import looks_like_bot
from linguaalayam.observability.queries import log_request

log = logging.getLogger(__name__)


def log_feature_event(
    route_type: str,
    request: Request,
    *,
    query: str | None = None,
    status_code: int = 200,
) -> None:
    """Best-effort insert of one analytics row for a feature usage event.

    Never raises — a logging failure must not break the request that triggered it.

    Parameters
    ----------
    route_type : str
        Analytics classification for this event (e.g. "varnam", "jayasree").
    request : Request
        The in-flight request the event occurred during; supplies IP/UA/country.
    query : str | None, optional
        Free-form detail for this event (e.g. the manglish word Varnam converted).
    status_code : int, optional
        Status to record, by default 200
    """
    try:
        user_agent = request.headers.get("user-agent")
        session_factory = get_session_factory()
        with get_session(session_factory) as session:
            log_request(
                session,
                method=request.method,
                path=request.url.path,
                route_type=route_type,
                query=query,
                status_code=status_code,
                duration_ms=0.0,
                ip=client_ip(request),
                country=request.headers.get("cf-ipcountry"),
                user_agent=user_agent,
                is_bot=looks_like_bot(user_agent),
            )
    except Exception:  # pragma: no cover — logging must never break a request
        log.warning("Failed to record feature event %r", route_type, exc_info=True)
