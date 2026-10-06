import logging
from collections.abc import Awaitable, Callable
from functools import wraps

from sqlalchemy.exc import SQLAlchemyError

from core.exceptions import StorageError

logger = logging.getLogger(__name__)


def translate_storage_errors[**P, R](
    method: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    @wraps(method)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await method(*args, **kwargs)
        except (SQLAlchemyError, OSError) as error:
            logger.exception("%s failed with error: %s", method.__qualname__, str(error))
            raise StorageError() from error

    return wrapper
