from pathlib import Path

import pytest

from django_autotyping.codemodding.django_utils import DjangoContext


@pytest.fixture(scope="session")
def sampleproject_context() -> DjangoContext:
    return DjangoContext("sampleproject.settings", Path(__file__).parent / "sampleproject", False)
