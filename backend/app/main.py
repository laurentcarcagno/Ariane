from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app import migrate
from app.database import make_sessionmaker
from app.routers import api
from app.services.customers import load_customers
from app.services.secrets import fetch_secrets, resolve_database_url


def create_app(settings: Settings | None = None) -> FastAPI:
    s = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        secrets = fetch_secrets(s)
        engine, maker = make_sessionmaker(resolve_database_url(s, secrets))
        app.state.sessionmaker = maker
        async with engine.begin() as conn:
            await conn.run_sync(migrate.upgrade)
        yield
        await engine.dispose()

    app = FastAPI(title="ARIANE", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)
    app.state.settings = s
    app.state.customers = load_customers(s.customers_config_path)
    app.include_router(api.router)
    return app


app = create_app()
