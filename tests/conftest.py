from pathlib import Path

import pytest

from django_autotyping.codemodding.django_context import DjangoCodemodContext


@pytest.fixture(scope="session")
def sampleproject_context() -> DjangoCodemodContext:
    return DjangoCodemodContext("sampleproject.settings", Path(__file__).parent / "sampleproject", False)
