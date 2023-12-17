from __future__ import annotations

import inspect
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from django.conf import ENVIRONMENT_VARIABLE as DJANGO_SETTINGS_MODULE_ENV_KEY

from ..compat import is_relative_to
from .models import ModelInfo

if TYPE_CHECKING:
    from django.apps.registry import Apps
    from django.conf import LazySettings


@contextmanager
def _temp_environ() -> Iterator[None]:
    """Allow the ability to set os.environ temporarily"""
    environ = dict(os.environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(environ)


def initialize_django(settings_module: str, app_path: Path) -> tuple[Apps, LazySettings]:
    with _temp_environ():
        os.environ[DJANGO_SETTINGS_MODULE_ENV_KEY] = settings_module

        # Patching `sys.path` to allow Django to setup correctly
        sys.path.append(str(app_path))

        from django.apps import apps
        from django.conf import settings

        apps.get_swappable_settings_name.cache_clear()  # type: ignore[attr-defined]
        apps.clear_cache()

        if not settings.configured:
            settings._setup()  # type: ignore[misc]
        apps.populate(settings.INSTALLED_APPS)

    assert apps.apps_ready, "Apps are not ready"
    assert settings.configured, "Settings are not configured"

    return apps, settings


class DjangoContext:
    def __init__(self, django_settings_module: str, root_dir: Path, assume_class_getitem: bool) -> None:
        self.django_settings_module = django_settings_module
        self.root_dir = root_dir
        self.apps, self.settings = initialize_django(self.django_settings_module, root_dir)
        self.assume_class_getitem = assume_class_getitem

    @property
    def model_infos(self) -> list[ModelInfo]:
        """A list of `ModelInfo` objects.

        Only the models defined in files relative to `self.root_dir` will be taken into account.
        """
        return [
            ModelInfo.from_model(model)
            for model in self.apps.get_models()
            if is_relative_to(Path(inspect.getabsfile(model)), self.root_dir.resolve())
        ]
