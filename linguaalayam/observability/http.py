"""Request-metadata helpers shared by the ASGI middleware and one-off feature events."""

from starlette.requests import Request


def client_ip(request: Request) -> str | None:
    """Best-guess client IP — prefers Cloudflare's header, falls back to the transport address."""
    return request.headers.get("cf-connecting-ip") or (
        request.client.host if request.client else None
    )
