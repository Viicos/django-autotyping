from __future__ import annotations

from importlib import import_module
from typing import Any, Union, cast

from django.apps.registry import Apps
from django.conf import LazySettings
from django.db.models import NOT_PROVIDED, DateField, Field
from django.urls import URLPattern, URLResolver
from django.urls.converters import StringConverter
from django.urls.resolvers import RegexPattern, RoutePattern
from libcst.codemod.visitors import ImportItem

from django_autotyping.typing import ModelType

from .codemods.utils import to_pascal


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
    def reverse_lookups(self) -> dict[str, dict[str, tuple[Any, bool]]]:
        """A mapping between viewnames to be used with `reverse` and the available lookup arguments."""
        patterns = cast(list[Union[URLResolver, URLPattern]], import_module(self.settings.ROOT_URLCONF).urlpatterns)
        return _get_reverse_map(patterns)

    def is_duplicate(self, model: ModelType) -> bool:
        """Whether the model has a duplicate name with another model in a different app."""
        return len([m for m in self.models if m.__name__ == model.__name__]) >= 2  # noqa: PLR2004

    def get_model_name(self, model: ModelType) -> str:
        """Return the name of the model in the context of a stub file.

        If the model has a duplicate name, an alias is returned.
        """
        return self._get_model_alias(model) if self.is_duplicate(model) else model.__name__

    def is_optional(self, field: Field) -> bool:
        """Determine if a field requires a value to be provided when instantiating a model.

        In practice, there isn't any reliable way to determine this (even if Django does not provide
        a default, things could be set at the database level). However, we can make some assumptions
        regarding the field instance, see https://forum.djangoproject.com/t/26357 for more details.
        """
        return (
            field.null
            or field.has_default()
            or getattr(field, "db_default", NOT_PROVIDED) is not NOT_PROVIDED  # No `has_db_default` method :/
            or isinstance(field, DateField)
            and (field.auto_now or field.auto_now_add)
        )


def _get_reverse_map(
    url_patterns: list[URLResolver | URLPattern], parent_namespaces: list[str] | None = None
) -> dict[str, dict[str, tuple[Any, bool]]]:
    """Build a mapping between view names usable as a lookup with `reverse` and a mapping between
    the views arguments and a two-tuple (the converter instance and a boolean indicating whether
    the argument is required).
    """
    if parent_namespaces is None:
        parent_namespaces = []
    paths_info = {}

    for pattern in reversed(url_patterns):  # Parsing in reverse is important!
        if isinstance(pattern, URLResolver):
            new_parent_namespaces = parent_namespaces.copy()
            if pattern.namespace:
                new_parent_namespaces.append(pattern.namespace)
            paths_info = {
                **paths_info,
                **_get_reverse_map(pattern.url_patterns, parent_namespaces=new_parent_namespaces),
            }
        elif isinstance(pattern, URLPattern) and pattern.name:
            key = ":".join(parent_namespaces)
            if key:
                key += ":"
            key += pattern.name

            if isinstance(pattern.pattern, RoutePattern):
                paths_info[key] = {k: (v, k not in pattern.default_args) for k, v in pattern.pattern.converters.items()}
            elif isinstance(pattern.pattern, RegexPattern):
                # We extract named regex groups from the `re.Pattern` object,
                # and assume the converter is a `StringConverter`
                # (the codemod will map the type hint accordingly).
                # Unnamed groups are not supported, and discouraged anyway
                paths_info[key] = {
                    k: (StringConverter(), k not in pattern.default_args)
                    for k in pattern.pattern.regex.groupindex.keys()
                }

    return paths_info
