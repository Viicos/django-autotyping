from __future__ import annotations

import inspect
from pathlib import Path

import django
from django.apps import apps

from .compat import is_relative_to
from .models import ModelInfo
from .typing import ModelType


def setup_django() -> None:
    django.setup()


def _discover_models(root_dir: Path) -> list[ModelType]:
    """Discover models for all installed apps of the current project.

    Only the apps defined relative to `root_dir` will be returned.
    """
    return [model for model in apps.get_models() if is_relative_to(Path(inspect.getabsfile(model)), root_dir)]


def parse_models(root_dir: Path) -> list[ModelInfo]:
    return [ModelInfo.from_model(model) for model in _discover_models(root_dir.resolve())]
