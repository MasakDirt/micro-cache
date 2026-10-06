import asyncio
import logging
from collections.abc import Sequence

from core.exceptions import TransformerError
from core.repos.transformed_strings import TransformedStringRepository
from core.services.hashing import HashingService
from core.services.transformer import Transformer
from db.models import TransformedString

logger = logging.getLogger(__name__)


class TransformCache:
    def __init__(
        self,
        repo: TransformedStringRepository,
        transformer: Transformer,
        hashing: HashingService,
        concurrency: int,
    ) -> None:
        self._repo = repo
        self._transformer = transformer
        self._hashing = hashing
        self._semaphore = asyncio.Semaphore(concurrency)

    async def transform_all(self, texts: Sequence[str]) -> dict[str, str]:
        unique = list(dict.fromkeys(texts))
        keys = {text: self._hashing.string_key(text) for text in unique}
        cached = await self._repo.get_outputs(list(keys.values()))
        outputs = {text: cached[key] for text, key in keys.items() if key in cached}
        misses = [text for text in unique if text not in outputs]

        try:
            transformed = await asyncio.gather(*(self._transform(text) for text in misses))
        except Exception as error:
            logger.exception("transformer failed")
            raise TransformerError() from error

        await self._repo.add(
            [
                TransformedString(
                    hash=keys[text],
                    input=text,
                    output=output,
                    transformer_version=self._transformer.version,
                )
                for text, output in zip(misses, transformed, strict=True)
            ]
        )

        return outputs | dict(zip(misses, transformed, strict=True))

    async def _transform(self, text: str) -> str:
        async with self._semaphore:
            return await self._transformer.transform(text)
