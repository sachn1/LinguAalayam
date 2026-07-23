"""Query functions for request-level traffic and usage analytics."""

import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from linguaalayam.observability.models import RequestLog

_SEARCH_ROUTE_TYPES = ("web_search", "lookup_exact", "lookup_fuzzy", "lookup_semantic")


def log_request(
    session: Session,
    *,
    method: str,
    path: str,
    route_type: str,
    query: str | None,
    status_code: int,
    duration_ms: float,
    ip: str | None,
    country: str | None,
    user_agent: str | None,
    is_bot: bool,
) -> None:
    """Insert one traffic/usage analytics row for an inbound HTTP request.

    Parameters
    ----------
    session : Session
        SQLAlchemy session to use for the insert.
    method : str
        HTTP method (e.g. "GET").
    path : str
        Request path, excluding query string.
    route_type : str
        Coarse route category (e.g. "web_search", "lookup_exact", "mcp", "other").
    query : str | None
        Search term extracted from the ``query`` query-string parameter, if present.
    status_code : int
        HTTP response status code.
    duration_ms : float
        Request handling time in milliseconds.
    ip : str | None
        Client IP address.
    country : str | None
        Two-letter country code, if available.
    user_agent : str | None
        Raw User-Agent header.
    is_bot : bool
        Heuristic guess that the request is automated.
    """
    session.add(
        RequestLog(
            method=method,
            path=path,
            route_type=route_type,
            query=query,
            status_code=status_code,
            duration_ms=duration_ms,
            ip=ip,
            country=country,
            user_agent=user_agent,
            is_bot=is_bot,
        )
    )


def traffic_by_route_type(session: Session, since: datetime.datetime) -> list[tuple[str, int, int]]:
    """Return (route_type, request_count, bot_count) since a given timestamp.

    Parameters
    ----------
    session : Session
        SQLAlchemy session to use for the query.
    since : datetime.datetime
        Only count requests logged at or after this timestamp.
    """
    stmt = (
        select(
            RequestLog.route_type,
            func.count().label("count"),
            func.count().filter(RequestLog.is_bot).label("bot_count"),
        )
        .where(RequestLog.timestamp >= since)
        .group_by(RequestLog.route_type)
        .order_by(desc("count"))
    )
    return [(row.route_type, row.count, row.bot_count) for row in session.execute(stmt)]


def top_queries(
    session: Session, since: datetime.datetime, limit: int = 10
) -> list[tuple[str, int]]:
    """Return the most frequent search terms since a given timestamp.

    Restricted to search/lookup route types so outbound-click labels (which
    reuse the same ``query`` column — see ``RequestLog.query``) don't show up
    here as if they were dictionary lookups.

    Parameters
    ----------
    session : Session
        SQLAlchemy session to use for the query.
    since : datetime.datetime
        Only count requests logged at or after this timestamp.
    limit : int, optional
        Maximum number of terms to return, by default 10
    """
    stmt = (
        select(RequestLog.query, func.count().label("count"))
        .where(
            RequestLog.timestamp >= since,
            RequestLog.route_type.in_(_SEARCH_ROUTE_TYPES),
            RequestLog.query.isnot(None),
            RequestLog.query != "",
        )
        .group_by(RequestLog.query)
        .order_by(desc("count"))
        .limit(limit)
    )
    return [(row.query, row.count) for row in session.execute(stmt)]


def top_outbound_clicks(
    session: Session, since: datetime.datetime, limit: int = 10
) -> list[tuple[str, int]]:
    """Return click counts for outbound links (How to use, GitHub, etc.) since a timestamp.

    Parameters
    ----------
    session : Session
        SQLAlchemy session to use for the query.
    since : datetime.datetime
        Only count requests logged at or after this timestamp.
    limit : int, optional
        Maximum number of labels to return, by default 10
    """
    stmt = (
        select(RequestLog.query, func.count().label("count"))
        .where(RequestLog.timestamp >= since, RequestLog.route_type == "outbound_click")
        .group_by(RequestLog.query)
        .order_by(desc("count"))
        .limit(limit)
    )
    return [(row.query, row.count) for row in session.execute(stmt)]


def top_clients(
    session: Session, since: datetime.datetime, limit: int = 10
) -> list[tuple[str, str | None, int, bool]]:
    """Return the most active clients (by IP) since a given timestamp.

    Parameters
    ----------
    session : Session
        SQLAlchemy session to use for the query.
    since : datetime.datetime
        Only count requests logged at or after this timestamp.
    limit : int, optional
        Maximum number of clients to return, by default 10

    Returns
    -------
    list[tuple[str, str | None, int, bool]]
        ``(ip, country, request_count, is_bot)`` tuples, ordered by request count descending.
        ``is_bot`` reflects whether the majority of that IP's requests were flagged as automated.
    """
    stmt = (
        select(
            RequestLog.ip,
            func.max(RequestLog.country).label("country"),
            func.count().label("count"),
            (func.count().filter(RequestLog.is_bot) * 2 > func.count()).label("mostly_bot"),
        )
        .where(RequestLog.timestamp >= since, RequestLog.ip.isnot(None))
        .group_by(RequestLog.ip)
        .order_by(desc("count"))
        .limit(limit)
    )
    return [(row.ip, row.country, row.count, bool(row.mostly_bot)) for row in session.execute(stmt)]


def top_user_agents(
    session: Session, since: datetime.datetime, limit: int = 10
) -> list[tuple[str, int, bool]]:
    """Return the most common User-Agent strings since a given timestamp.

    Lets the dashboard show what's actually generating traffic (specific
    crawler/bot names, MCP client SDKs, browsers) instead of just a bot/not-bot
    flag on the client IP table.

    Parameters
    ----------
    session : Session
        SQLAlchemy session to use for the query.
    since : datetime.datetime
        Only count requests logged at or after this timestamp.
    limit : int, optional
        Maximum number of user agents to return, by default 10

    Returns
    -------
    list[tuple[str, int, bool]]
        ``(user_agent, request_count, is_bot)`` tuples, ordered by request count
        descending. ``is_bot`` reflects whether the majority of that UA's
        requests were flagged as automated.
    """
    stmt = (
        select(
            RequestLog.user_agent,
            func.count().label("count"),
            (func.count().filter(RequestLog.is_bot) * 2 > func.count()).label("mostly_bot"),
        )
        .where(RequestLog.timestamp >= since, RequestLog.user_agent.isnot(None))
        .group_by(RequestLog.user_agent)
        .order_by(desc("count"))
        .limit(limit)
    )
    return [(row.user_agent, row.count, bool(row.mostly_bot)) for row in session.execute(stmt)]
