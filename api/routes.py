from uuid import UUID

from fastapi import APIRouter, Response, status

from api.dependencies import (
    HealthRepositoryDep,
    PayloadServiceDep,
    TransformerDep,
    ValidPayloadRequest,
)
from core.schemas import ErrorResponse, Health, PayloadCreated, PayloadRead, Stats

router = APIRouter()

ERROR = {"model": ErrorResponse}


@router.post(
    "/payload",
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"model": PayloadCreated},
        413: ERROR,
        422: ERROR,
        502: ERROR,
        503: ERROR,
    },
)
async def create_payload(
    request: ValidPayloadRequest, service: PayloadServiceDep, response: Response
) -> PayloadCreated:
    created = await service.create(request)
    response.status_code = status.HTTP_201_CREATED if created.created else status.HTTP_200_OK
    return created


@router.get("/payload/{payload_id}", responses={404: ERROR, 422: ERROR, 503: ERROR})
async def read_payload(payload_id: UUID, service: PayloadServiceDep) -> PayloadRead:
    return await service.get(payload_id)


@router.get("/stats")
async def read_stats(transformer: TransformerDep) -> Stats:
    return Stats(transformer_calls=transformer.calls, transformer_version=transformer.version)


@router.get("/health", responses={503: ERROR})
async def read_health(health: HealthRepositoryDep) -> Health:
    await health.ping()
    return Health(status="ok")
