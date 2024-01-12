from pathlib import Path

import pytest
from helpers import initialize_django

from django_autotyping.codemodding.django_context import DjangoCodemodContext
from django_autotyping.stubbing.django_context import DjangoStubbingContext


@pytest.fixture(scope="session")
def codemodtestproj_context() -> DjangoCodemodContext:
    project_dir = Path(__file__).parent / "codemodtestproj"
    apps, settings = initialize_django("codemodtestproj.settings", project_dir)
    return DjangoCodemodContext(apps, settings, project_dir)


@pytest.fixture(scope="session")
def stubstestproj_context() -> DjangoStubbingContext:
    project_dir = Path(__file__).parent / "stubstestproj"
    apps, settings = initialize_django("settings", project_dir)
    return DjangoStubbingContext(apps, settings)
