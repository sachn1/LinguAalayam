"""ORM model for request-level traffic and usage analytics."""

import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from linguaalayam.models.orm import Base


class RequestLog(Base):
    """One row per inbound HTTP request, for traffic and usage analytics.

    Populated by ``linguaalayam.observability.middleware.RequestLoggingMiddleware``
    so the owner can see which routes, search terms, and clients drive traffic —
    the detail Cloudflare's free-tier analytics can't provide.

    Attributes
    ----------
    id : int
        Auto-incrementing primary key.
    timestamp : datetime
        Server-side timestamp set on insert.
    method : str
        HTTP method (e.g. ``"GET"``).
    path : str
        Request path, excluding query string.
    route_type : str
        Coarse route category: ``"web_search"``, ``"lookup_exact"``,
        ``"lookup_fuzzy"``, ``"lookup_semantic"``, ``"mcp"``, or ``"other"``.
    query : str | None
        Search term (from the ``query`` param) or outbound-click label (from the
        ``label`` param), depending on ``route_type`` — whichever is present.
    status_code : int
        HTTP response status code.
    duration_ms : float
        Request handling time in milliseconds.
    ip : str | None
        Client IP — prefers the ``CF-Connecting-IP`` header, falls back to the
        ASGI transport address.
    country : str | None
        Two-letter country code from the ``CF-IPCountry`` header, if present.
    user_agent : str | None
        Raw ``User-Agent`` header.
    is_bot : bool
        Heuristic guess (user-agent pattern match) that the request is automated.
        Not authoritative — Cloudflare's real bot score is an Enterprise feature.
    """

    __tablename__ = "request_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    method: Mapped[str] = mapped_column(Text, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    route_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    ip: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        """Return a concise string representation showing id, path, and status."""
        return f"<RequestLog id={self.id} path={self.path!r} status={self.status_code}>"
