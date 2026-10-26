from fastapi import FastAPI

from app.routers import api


def create_app() -> FastAPI:
    app = FastAPI(title="ARIANE", docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.include_router(api.router)
    return app


app = create_app()
