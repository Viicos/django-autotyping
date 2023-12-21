from django.apps import AppConfig
from django.db.models.signals import post_migrate


class DjangoAutotypingAppConfig(AppConfig):
    name = "django_autotyping"

    def ready(self) -> None:
        from .stubbing import post_migrate_receiver

        post_migrate.connect(post_migrate_receiver, sender=self)
        return super().ready()
