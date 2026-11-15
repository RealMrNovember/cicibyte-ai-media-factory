from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from mediafactory import __version__
from mediafactory.api.body_limit import MaxBodySizeMiddleware
from mediafactory.api.routes import activity, backgrounds, settings_io, system, music, voices, source_catalog, schedules, concepts, youtube, instagram, stock, audit, auth, items, jobs, providers, source_credentials, sources, task_routes
from mediafactory.core.config import Settings, get_settings

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; "
        "style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'self'"
    ),
}


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="CiciByte AI Media Factory", version=__version__, docs_url=None, redoc_url=None, openapi_url=None
    )
    app.state.settings = settings
    app.state.health_engine = create_engine(
        settings.database_url, pool_pre_ping=True, pool_size=1, max_overflow=0, connect_args={"connect_timeout": 3}
    )

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    # Outermost: rewrite client address and scheme from trusted reverse proxies (Caddy, tailscale serve, Docker).
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=settings.trusted_proxies)
    app.add_middleware(MaxBodySizeMiddleware)  # outermost: refuse huge bodies before parsing or auth

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    @app.get("/api/health", tags=["system"])
    def health() -> JSONResponse:
        try:
            with app.state.health_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return JSONResponse(status_code=503, content={"status": "degraded", "db": "down", "version": __version__})
        return JSONResponse(content={"status": "ok", "db": "up", "version": __version__})

    app.include_router(auth.router)
    app.include_router(audit.router)
    app.include_router(providers.router)
    app.include_router(task_routes.router)
    app.include_router(source_credentials.router)
    app.include_router(items.router)
    app.include_router(source_catalog.router)  # before sources: '/catalog' must not match '/{sid}'
    app.include_router(sources.router)
    app.include_router(jobs.router)
    app.include_router(backgrounds.router)
    app.include_router(stock.router)
    app.include_router(schedules.router)
    app.include_router(concepts.router)
    app.include_router(youtube.router)
    app.include_router(instagram.router)
    app.include_router(voices.router)
    app.include_router(voices.dictionary)
    app.include_router(music.router)
    app.include_router(system.router)
    app.include_router(settings_io.router)
    app.include_router(activity.router)

    # Panel (static, no build step). Mounted last so /api/* keeps priority.
    from pathlib import Path

    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent.parent / "web", html=True), name="panel")
    return app
