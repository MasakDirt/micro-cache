import pytest

from core.services.transformer import UpperCaseTransformer


@pytest.fixture
def transformer() -> UpperCaseTransformer:
    return UpperCaseTransformer(delay_seconds=0)
