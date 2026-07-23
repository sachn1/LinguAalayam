"""Public endpoint for client-side click tracking.

Covers two kinds of clicks the generic RequestLoggingMiddleware can't classify
correctly on its own: outbound links with no server route at all (external
GitHub pages), and in-app feature buttons that either do nothing server-side
(handwriting trace) or just re-fire an existing route (the romanise toggle
re-triggers /search) — in both cases the click itself is the analytics event,
not the HTTP request it may or may not cause.
"""

from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse

from linguaalayam.observability.events import log_feature_event

router = APIRouter(include_in_schema=False)

# label -> route_type. An allow-list (rather than using the label as the
# route_type directly) keeps this public, unauthenticated endpoint from being
# used to stuff request_log with arbitrary route_type values.
_CLICK_LABEL_ROUTES: dict[str, str] = {
    # Outbound links with no server route of their own.
    "how_to_use": "outbound_click",
    "data_sources": "outbound_click",
    "github": "outbound_click",
    "open_issue": "outbound_click",
    "mlmorph": "outbound_click",
    # In-app feature buttons, classified under the package/feature they use.
    "jayasree": "jayasree",
    "ml2en": "ml2en",
    "web_speech": "web_speech",
}


@router.post("/track/click")
def track_click(label: str, request: Request) -> Response:
    """Record a client-side click — see module docstring for why this exists."""
    route_type = _CLICK_LABEL_ROUTES.get(label)
    if route_type is None:
        return PlainTextResponse("unknown label", status_code=400)
    log_feature_event(route_type, request, query=label, status_code=204)
    return Response(status_code=204)
