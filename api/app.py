from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.errors import register_error_handlers
from api.routes import router
from core.logging_config import configure_logging
from core.services.transformer import UpperCaseTransformer
from core.settings import Settings, get_settings
from db.session import build_engine, build_session_factory


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine = build_engine(settings)
    app.state.session_factory = build_session_factory(engine)
    app.state.transformer = UpperCaseTransformer(delay_seconds=settings.transformer_delay_seconds)
    yield
    await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="micro-cache", lifespan=lifespan)
    app.state.settings = settings
    register_error_handlers(app)
    app.include_router(router)
    return app
