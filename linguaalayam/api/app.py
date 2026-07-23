"""FastAPI REST layer over LinguAalayam's DictionaryTools."""

import json
import os
import subprocess
import time
from contextlib import asynccontextmanager
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any, Literal

import uvicorn
from fastapi import FastAPI, Query, Response
from fastapi.staticfiles import StaticFiles
from httpx import ASGITransport, AsyncClient
from omegaconf import OmegaConf
from pydantic import BaseModel
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request

from linguaalayam.api.admin import router as _admin_router
from linguaalayam.api.dependencies import get_tools, set_session_factory, set_tools, set_translator
from linguaalayam.api.web import router as _web_router
from linguaalayam.database import build_engine, build_session_factory
from linguaalayam.embeddings import EmbeddingService
from linguaalayam.env import load_env
from linguaalayam.mcp.remote import get_mcp_app, mcp
from linguaalayam.observability import RequestLoggingMiddleware
from linguaalayam.observability import click_tracking_router as _click_tracking_router
from linguaalayam.rag.tools import DictionaryTools
from linguaalayam.translation import build_translation_service

load_env()

# _CACHE_1D is a one-day HTTP cache directive
# reused by multiple routes.
_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
_CACHE_1D = "public, max-age=86400"
_PLAY_CONSOLE_APP_CERT_FINGERPINT = (
    "36:00:69:0E:1F:3B:32:5F:1E:F1:B4:55:EE:DD:67:AA:"
    "88:D6:D8:3A:27:6E:25:DB:F8:09:EF:DF:02:C0:CB:04"
)


try:
    _VERSION = _pkg_version("linguaalayam")
except Exception:
    _VERSION = "dev"

CorpusSource = Literal["olam_enml", "datuk", "ekkurup", "sayahna"]


def _ensure_docker_db() -> None:
    """Start the DB container if it exists but is not running (bare local dev only)."""
    container = os.getenv("DB_CONTAINER", "linguaalayam")
    try:
        result = subprocess.run(
            ["docker", "start", container],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            time.sleep(2)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def _init_tools() -> DictionaryTools:
    """Build DictionaryTools from environment variables."""
    db_cfg = OmegaConf.create(
        {
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", ""),
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "name": os.getenv("DB_NAME", "linguaalayam"),
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
        }
    )
    embed_cfg = OmegaConf.create(
        {
            "model": os.getenv("EMBED_MODEL", _EMBED_MODEL),
            "batch_size": 256,
            "normalize": True,
            "quantise": False,
        }
    )
    engine = build_engine(db_cfg)
    session_factory = build_session_factory(engine)
    set_session_factory(session_factory)
    service = EmbeddingService(embed_cfg)
    return DictionaryTools(session_factory, service)


@asynccontextmanager
async def _lifespan(_: FastAPI):
    """Initialise tools, translator, and MCP session manager at application startup."""
    _ensure_docker_db()
    set_tools(_init_tools())
    set_translator(build_translation_service(os.getenv("TRANSLATION_BACKEND", "marian")))
    # The MCP sub-app is mount()ed, so Starlette never runs its lifespan — start
    # the streamable-HTTP session manager here or every MCP request 500s.
    async with mcp.session_manager.run():
        yield


class LookupResult(BaseModel):
    """Pydantic response model for a single dictionary lookup result."""

    headword: str
    source: str
    entry_type: str
    embed_text: str
    data: dict[str, Any]
    match_type: str
    score: float


app = FastAPI(
    title="linguaalayam",
    description="Abode of words.",
    version=_VERSION,
    lifespan=_lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(RequestLoggingMiddleware)

_STATIC = Path(__file__).resolve().parents[1] / "static"
_mcp_starlette = get_mcp_app()

app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")
app.include_router(_web_router)
app.include_router(_admin_router)
app.include_router(_click_tracking_router)
app.mount("/mcp", _mcp_starlette)


def _protected_resource_metadata() -> dict:
    """RFC 9728 protected resource metadata body."""
    from linguaalayam.mcp.remote import _ISSUER_URL

    resource = _ISSUER_URL.rstrip("/")
    return {
        "resource": resource,
        "authorization_servers": [resource],
        "scopes_supported": ["dictionary"],
        "bearer_methods_supported": ["header"],
    }


async def _authorization_server_metadata() -> tuple[int, Any]:
    """RFC 8414 AS metadata, proxied from FastMCP's sub-app.

    Patches token_endpoint_auth_methods to advertise "none" so public PKCE
    clients (Claude desktop/web connectors) don't abort on metadata inspection.
    Returns (status_code, body) where body is a dict on success.
    """
    async with AsyncClient(
        transport=ASGITransport(app=_mcp_starlette), base_url="http://localhost"
    ) as client:
        r = await client.get("/.well-known/oauth-authorization-server")

    if r.status_code != 200:
        return r.status_code, None
    meta = r.json()
    for field in (
        "token_endpoint_auth_methods_supported",
        "revocation_endpoint_auth_methods_supported",
    ):
        if "none" not in (meta.get(field) or []):
            meta[field] = ["none", *meta.get(field, [])]
    return 200, meta


# RFC 9728 — both the domain root and the path-aware variant. Clients differ on
# which they probe; serve both so discovery never 404s.
@app.get("/.well-known/oauth-protected-resource", include_in_schema=False)
@app.get("/.well-known/oauth-protected-resource/", include_in_schema=False)
@app.get("/.well-known/oauth-protected-resource/mcp", include_in_schema=False)
@app.get("/.well-known/oauth-protected-resource/mcp/", include_in_schema=False)
async def oauth_protected_resource_metadata() -> Response:
    """Serve RFC 9728 protected resource metadata for MCP OAuth discovery."""
    return Response(
        content=json.dumps(_protected_resource_metadata()),
        media_type="application/json",
    )


# RFC 8414 — the issuer URL carries a path ("/mcp"), so a compliant client inserts
# the well-known segment BEFORE the path (".../.well-known/oauth-authorization-server/mcp").
# Serve the root, the path-aware, and the path-appended variants — plus the OIDC
# discovery alias some clients probe — all patched identically so every client's
# discovery strategy lands on consistent metadata.
@app.get("/.well-known/oauth-authorization-server", include_in_schema=False)
@app.get("/.well-known/oauth-authorization-server/mcp", include_in_schema=False)
@app.get("/.well-known/oauth-authorization-server/mcp/", include_in_schema=False)
@app.get("/.well-known/openid-configuration", include_in_schema=False)
@app.get("/.well-known/openid-configuration/mcp", include_in_schema=False)
async def oauth_discovery() -> Response:
    """Serve RFC 8414 authorization server metadata for OAuth discovery."""
    status, meta = await _authorization_server_metadata()
    if status != 200:
        return Response(status_code=status, media_type="application/json")
    return Response(content=json.dumps(meta), media_type="application/json")


# Root-level OAuth endpoints. The MCP TS SDK (Inspector, Claude desktop/web) treats
# the authorization server as the ORIGIN root — it POSTs to /token, /authorize,
# /register, /revoke at the domain root, ignoring the metadata's path-scoped
# endpoints. FastMCP only mounts them under /mcp, so proxy the root paths into the
# sub-app. This makes the server tolerant of both origin-based and path-aware clients.
_PROXY_HOP_BY_HOP = {"host", "content-length", "transfer-encoding", "content-encoding"}


async def _proxy_to_mcp(request: Request, subpath: str) -> Response:
    """Forward a root-level OAuth request to the MCP sub-app at ``subpath``."""
    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in _PROXY_HOP_BY_HOP}
    async with AsyncClient(
        transport=ASGITransport(app=_mcp_starlette),
        base_url="http://localhost",
        follow_redirects=False,
    ) as client:
        r = await client.request(
            request.method,
            subpath,
            params=request.query_params,
            content=body,
            headers=headers,
        )
    out = {k: v for k, v in r.headers.items() if k.lower() not in _PROXY_HOP_BY_HOP}
    return Response(content=r.content, status_code=r.status_code, headers=out)


@app.api_route("/authorize", methods=["GET", "POST"], include_in_schema=False)
async def oauth_authorize(request: Request) -> Response:
    """Proxy root /authorize to the MCP sub-app."""
    return await _proxy_to_mcp(request, "/authorize")


@app.post("/token", include_in_schema=False)
async def oauth_token(request: Request) -> Response:
    """Proxy root /token to the MCP sub-app."""
    return await _proxy_to_mcp(request, "/token")


@app.post("/register", include_in_schema=False)
async def oauth_register(request: Request) -> Response:
    """Proxy root /register to the MCP sub-app."""
    return await _proxy_to_mcp(request, "/register")


@app.post("/revoke", include_in_schema=False)
async def oauth_revoke(request: Request) -> Response:
    """Proxy root /revoke to the MCP sub-app."""
    return await _proxy_to_mcp(request, "/revoke")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe — returns HTTP 200 when the server is running."""
    return {"status": "ok"}


# TWA (Trusted Web Activity) domain verification for Android app.
# The SHA256 fingerprint below is a placeholder — replace it with the actual
# signing certificate fingerprint from Google Play Console after creating the
# app (App signing → App signing key certificate → SHA-256 certificate fingerprint).
_ASSETLINKS = json.dumps(
    [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": "org.linguaalayam.app",
                "sha256_cert_fingerprints": [_PLAY_CONSOLE_APP_CERT_FINGERPINT],
            },
        }
    ],
    indent=2,
)


@app.get("/.well-known/assetlinks.json", include_in_schema=False)
async def assetlinks() -> Response:
    """Serve TWA digital asset links for Android app domain verification."""
    return Response(content=_ASSETLINKS, media_type="application/json")


@app.get("/lookup/exact", response_model=list[LookupResult])
def exact_lookup(
    query: str = Query(..., max_length=500),
    source: CorpusSource | None = Query(default=None, description="Corpus to search"),
    response: Response = None,
) -> list[dict]:
    """Exact headword match (case-insensitive)."""
    response.headers["Cache-Control"] = _CACHE_1D
    return get_tools().exact_lookup(query, source=source)


@app.get("/lookup/fuzzy", response_model=list[LookupResult])
def fuzzy_lookup(
    query: str = Query(..., max_length=500),
    source: CorpusSource | None = Query(default=None, description="Corpus to search"),
    threshold: float = Query(default=0.3, ge=0.0, le=1.0, description="Minimum trigram similarity"),
    top_k: int = Query(default=10, ge=1, le=100),
    response: Response = None,
) -> list[dict]:
    """Trigram fuzzy headword search (pg_trgm)."""
    response.headers["Cache-Control"] = _CACHE_1D
    return get_tools().fuzzy_lookup(query, source=source, threshold=threshold, top_k=top_k)


@app.get("/lookup/semantic", response_model=list[LookupResult])
def semantic_lookup(
    query: str = Query(..., max_length=500),
    top_k: int = Query(default=5, ge=1, le=50),
    source: CorpusSource | None = Query(default=None, description="Corpus to search"),
    response: Response = None,
) -> list[dict]:
    """HNSW cosine semantic search via sentence embeddings."""
    response.headers["Cache-Control"] = _CACHE_1D
    return get_tools().semantic_lookup(query, top_k=top_k, source=source)


def main() -> None:  # pragma: no cover
    """Entry point for the API server (``poetry run api-server``)."""
    uvicorn.run(
        "linguaalayam.api.app:app",
        host="0.0.0.0",
        port=int(os.getenv("API_PORT", "8000")),
        reload=False,
    )
