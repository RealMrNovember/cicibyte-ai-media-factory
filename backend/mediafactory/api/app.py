from fastapi import FastAPI

from mediafactory import __version__
from mediafactory.api.routes import audit, auth


def create_app() -> FastAPI:
    app = FastAPI(title="CiciByte AI Media Factory", version=__version__, docs_url=None, redoc_url=None)
    app.include_router(auth.router)
    app.include_router(audit.router)
    return app
