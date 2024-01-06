from __future__ import annotations

import inspect
from pathlib import Path
from typing import TYPE_CHECKING

from django_autotyping._compat import is_relative_to

from .models import ModelInfo

if TYPE_CHECKING:
    from django.apps.registry import Apps
    from django.conf import LazySettings


class DjangoCodemodContext:
    def __init__(self, apps: Apps, settings: LazySettings, project_dir: Path) -> None:
        self.apps = apps
        self.settings = settings
        self.project_dir = project_dir

    @property
    def model_infos(self) -> list[ModelInfo]:
        """A list of `ModelInfo` objects.

        Only the models defined in files relative to `self.project_dir` will be taken into account.
        """
        return [
            ModelInfo.from_model(model)
            for model in self.apps.get_models()
            if is_relative_to(Path(inspect.getabsfile(model)), self.project_dir.resolve())
        ]
