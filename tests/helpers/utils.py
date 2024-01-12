from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from django.conf import ENVIRONMENT_VARIABLE as DJANGO_SETTINGS_MODULE_ENV_KEY

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

        apps.get_swappable_settings_name.cache_clear()
        apps.clear_cache()

        if not settings.configured:
            settings._setup()
        apps.populate(settings.INSTALLED_APPS)

    assert apps.apps_ready, "Apps are not ready"
    assert settings.configured, "Settings are not configured"

    return apps, settings
