from django.apps import AppConfig
from django.db.models.signals import post_migrate

from .stubbing import create_stubs, post_migrate_receiver


class DjangoAutotypingAppConfig(AppConfig):
    name = "django_autotyping"

    def ready(self) -> None:
        from .app_settings import AUTOTYPING_STUBS_DIR

        create_stubs(AUTOTYPING_STUBS_DIR)

        post_migrate.connect(post_migrate_receiver, sender=self)
        return super().ready()
