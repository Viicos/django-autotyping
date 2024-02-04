from __future__ import annotations

from collections import defaultdict

from django.apps.registry import Apps
from django.conf import LazySettings
from django.core.management import get_commands
from django.db.models import NOT_PROVIDED, DateField, Field
from django.urls import get_resolver
from libcst.codemod.visitors import ImportItem

from django_autotyping.typing import ModelType

from ..codemods._utils import to_pascal
from ._management_utils import CommandInfo, get_commands_infos
from ._url_utils import PathInfo, get_paths_infos


class DjangoStubbingContext:
    def __init__(self, apps: Apps, settings: LazySettings) -> None:
        self.apps = apps
        self.settings = settings

    @staticmethod
    def _get_model_alias(model: ModelType) -> str:
        """Return an alias of the model, by converting the app label to PascalCase and joining
        the app label to the model name.
        """
        app_label = to_pascal(model._meta.app_label)
        return f"{app_label}{model.__name__}"

    @property
    def models(self) -> list[ModelType]:
        """All the defined models."""
        return self.apps.get_models()

    @property
    def model_imports(self) -> list[ImportItem]:
        """A list of `ImportItem` instances.

        Can be used to easily import all models in a stub file.
        """

        return [
            ImportItem(
                module_name=model._meta.app_config.models_module.__name__,
                obj_name=model.__name__,
                alias=self._get_model_alias(model) if self.is_duplicate(model) else None,
            )
            for model in self.models
        ]

    @property
    def viewnames_lookups(self) -> defaultdict[str, PathInfo]:
        """A mapping between viewnames to be used with `reverse` and the available lookup arguments."""
        return get_paths_infos(get_resolver())

    @property
    def management_commands_info(self) -> dict[str, CommandInfo]:
        return get_commands_infos(get_commands())

    def is_duplicate(self, model: ModelType) -> bool:
        """Whether the model has a duplicate name with another model in a different app."""
        return len([m for m in self.models if m.__name__ == model.__name__]) >= 2  # noqa: PLR2004

    def get_model_name(self, model: ModelType) -> str:
        """Return the name of the model in the context of a stub file.

        If the model has a duplicate name, an alias is returned.
        """
        return self._get_model_alias(model) if self.is_duplicate(model) else model.__name__

    def get_field_nullability(self, field: Field) -> bool:
        """Determine if a field requires a value to be provided when instantiating a model.

        In practice, there isn't any reliable way to determine this (even if Django does not provide
        a default, things could be set at the database level). However, we can make some assumptions
        regarding the field instance, see https://forum.djangoproject.com/t/26357 for more details.
        """
        # TODO use the same logic as the mypy plugin
        return (
            field.null
            or field.has_default()
            or getattr(field, "db_default", NOT_PROVIDED) is not NOT_PROVIDED  # No `has_db_default` method :/
            or (isinstance(field, DateField) and (field.auto_now or field.auto_now_add))
        )