from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import PayloadTooLargeError
from core.repos.health import HealthRepository
from core.repos.payloads import PayloadRepository
from core.repos.transformed_strings import TransformedStringRepository
from core.schemas import PayloadRequest
from core.services.hashing import HashingService
from core.services.interleave import InterleaveService
from core.services.payload_service import PayloadService
from core.services.transform_cache import TransformCache
from core.services.transformer import Transformer
from core.settings import Settings
from db.session import open_session


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with open_session(request.app.state.session_factory) as session:
        yield session


def get_transformer(request: Request) -> Transformer:
    transformer: Transformer = request.app.state.transformer
    return transformer


SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
TransformerDep = Annotated[Transformer, Depends(get_transformer)]


def get_hashing(transformer: TransformerDep) -> HashingService:
    return HashingService(transformer.version)


def get_interleaver() -> InterleaveService:
    return InterleaveService()


def get_health_repository(session: SessionDep) -> HealthRepository:
    return HealthRepository(session)


def get_transform_cache(
    session: SessionDep,
    transformer: TransformerDep,
    hashing: Annotated[HashingService, Depends(get_hashing)],
    settings: SettingsDep,
) -> TransformCache:
    return TransformCache(
        repo=TransformedStringRepository(session),
        transformer=transformer,
        hashing=hashing,
        concurrency=settings.transformer_concurrency,
    )


def get_payload_service(
    session: SessionDep,
    cache: Annotated[TransformCache, Depends(get_transform_cache)],
    hashing: Annotated[HashingService, Depends(get_hashing)],
    interleaver: Annotated[InterleaveService, Depends(get_interleaver)],
) -> PayloadService:
    return PayloadService(
        payloads=PayloadRepository(session),
        cache=cache,
        hashing=hashing,
        interleaver=interleaver,
    )


def enforce_size_limits(request: PayloadRequest, settings: SettingsDep) -> PayloadRequest:
    for name, items in (("list_1", request.list_1), ("list_2", request.list_2)):
        if len(items) > settings.max_list_length:
            raise PayloadTooLargeError(name, settings.max_list_length, len(items))
    longest = max(len(text) for text in request.list_1 + request.list_2)
    if longest > settings.max_string_length:
        raise PayloadTooLargeError("string length", settings.max_string_length, longest)
    return request


PayloadServiceDep = Annotated[PayloadService, Depends(get_payload_service)]
HealthRepositoryDep = Annotated[HealthRepository, Depends(get_health_repository)]
ValidPayloadRequest = Annotated[PayloadRequest, Depends(enforce_size_limits)]
