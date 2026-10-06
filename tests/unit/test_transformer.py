from core.services.transformer import UpperCaseTransformer


async def test_upper_cases_text(transformer: UpperCaseTransformer) -> None:
    assert await transformer.transform("abc") == "ABC"


async def test_counts_every_call(transformer: UpperCaseTransformer) -> None:
    await transformer.transform("a")
    await transformer.transform("a")

    assert transformer.calls == 2


def test_version_is_v1(transformer: UpperCaseTransformer) -> None:
    assert transformer.version == "v1"
