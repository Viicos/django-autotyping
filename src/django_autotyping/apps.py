from typing import Any

from django.apps import AppConfig
from django.utils.autoreload import StatReloader, autoreload_started

from .stubbing import create_stubs


def receiver(sender: StatReloader, **kwargs: Any):
    pass


class DjangoAutotypingAppConfig(AppConfig):
    name = "django_autotyping"

    def ready(self) -> None:
        from .app_settings import AUTOTYPING_STUBS_DIR

        create_stubs(AUTOTYPING_STUBS_DIR)

        autoreload_started.connect(receiver)
        return super().ready()
