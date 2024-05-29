from django.apps import AppConfig


class AppwithoutmodelsmoduleConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "stubstestproj.appwithoutmodelsmodule"

    def ready(self) -> None:
        # See https://github.com/Viicos/django-autotyping/issues/59 for more context:
        from .extra_models import ExtraModel
