"""Admin-only traffic/usage analytics dashboard, gated behind HTTP Basic Auth."""

import datetime
import os
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from linguaalayam.api.dependencies import get_session_factory
from linguaalayam.api.web import _TEMPLATES
from linguaalayam.database import get_session
from linguaalayam.observability import (
    top_clients,
    top_outbound_clicks,
    top_queries,
    top_user_agents,
    traffic_by_route_type,
)

router = APIRouter(include_in_schema=False)
_basic_auth = HTTPBasic()


def _require_admin(credentials: Annotated[HTTPBasicCredentials, Depends(_basic_auth)]) -> None:
    """Validate HTTP Basic credentials against ADMIN_USER / ADMIN_PASSWORD env vars.

    Uses ``secrets.compare_digest`` for both fields to avoid timing side-channels.

    Raises
    ------
    HTTPException
        401 if credentials are missing, misconfigured, or don't match.
    """
    expected_user = os.getenv("ADMIN_USER")
    expected_password = os.getenv("ADMIN_PASSWORD")
    if not expected_user or not expected_password:
        raise HTTPException(status_code=503, detail="Admin auth not configured")

    user_ok = secrets.compare_digest(credentials.username, expected_user)
    password_ok = secrets.compare_digest(credentials.password, expected_password)
    if not (user_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


def _window_start(window_minutes: int) -> datetime.datetime:
    """Return the UTC timestamp marking the start of the requested lookback window."""
    return datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=window_minutes)


@router.get("/admin/analytics", response_class=HTMLResponse, dependencies=[Depends(_require_admin)])
def analytics_page(request: Request) -> HTMLResponse:
    """Serve the traffic/usage analytics dashboard shell."""
    return _TEMPLATES.TemplateResponse(request, "admin_analytics.html")


@router.get(
    "/admin/analytics/partial",
    response_class=HTMLResponse,
    dependencies=[Depends(_require_admin)],
)
def analytics_partial(
    request: Request,
    window_minutes: Annotated[int, Query(ge=1, le=10080)] = 60,
) -> HTMLResponse:
    """Return the HTMX-polled analytics fragment for the given lookback window."""
    since = _window_start(window_minutes)
    session_factory = get_session_factory()
    with get_session(session_factory) as session:
        routes = traffic_by_route_type(session, since)
        queries = top_queries(session, since, limit=10)
        clients = top_clients(session, since, limit=10)
        clicks = top_outbound_clicks(session, since, limit=10)
        user_agents = top_user_agents(session, since, limit=10)

    total_requests = sum(count for _, count, _ in routes)
    total_bots = sum(bot_count for _, _, bot_count in routes)

    return _TEMPLATES.TemplateResponse(
        request,
        "partials/admin_analytics_partial.html",
        {
            "window_minutes": window_minutes,
            "total_requests": total_requests,
            "total_bots": total_bots,
            "routes": routes,
            "queries": queries,
            "clients": clients,
            "clicks": clicks,
            "user_agents": user_agents,
        },
    )
