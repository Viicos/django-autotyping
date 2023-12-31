from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field

from django.apps.registry import Apps
from django.conf import LazySettings
from django.db.models import NOT_PROVIDED, DateField, Field
from django.urls import URLPattern, URLResolver, get_resolver
from libcst.codemod.visitors import ImportItem

from django_autotyping.typing import ModelType

from .codemods.utils import to_pascal


@dataclass(eq=True)
class PathInfo:
    # TODO refactor the structure
    kwargs_list: list[dict[str, bool]] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return all(kwargs == {} for kwargs in self.kwargs_list)

    def __hash__(self) -> int:
        raise NotImplementedError()  # TODO

    def get_kwargs_hash(self, kwargs: dict[str, bool]) -> str:
        return hashlib.sha1("".join(f"{k}={v}" for k, v in sorted(kwargs.items())))[:6]

    def add_kwargs_entry(self, kwargs: dict[str, bool]) -> None:
        # First, check for an existing entry with one key, e.g.:
        # `{"key": True}`
        # If the new entry has the same (and only!) key and this key is not required,
        # we update the existing entry and mark it as not required. We don't want to update
        # the entry if the new entry key is required, as it could have been marked as not
        # required previously.
        # This special case is to avoid having
        # `TypedDict("...", {"key": NotRequired[...]}) | TypedDict("...", {"key": ...})`
        # as a type hint.
        # TODO this should also work with multiple keys, but only when the exact same keys are present
        existing_entry = next((e for e in self.kwargs_list if e.keys() == kwargs.keys() and len(e) == 1), None)
        if existing_entry is not None and not list(kwargs.values())[0]:
            key = list(existing_entry.keys())[0]
            existing_entry[key] = False
        else:
            self.kwargs_list.append(kwargs)

    def get_typeddict_name(self, kwargs: dict[str, bool]) -> str:
        return f"_{self.get_kwargs_hash(kwargs).upper()}Kwargs"

    def get_kwargs_annotation(self) -> str:
        """Return the type annotation for the `kwargs` argument of `reverse`.

        In this context, `kwargs` refer to the function argument, not the kwargs of a view.
        """
        kwargs_str = [self.get_typeddict_name(kwargs) for kwargs in self.kwargs_list if kwargs]
        if {} in self.kwargs_list:
            kwargs_str.extend(["EmptyDict", "None"])

        return " | ".join(kwargs_str)

    def get_args_annotation(self, sequence_fallback: bool = True) -> str:
        """Return the type annotation for the `args` argument of `reverse`.

        If multiple URL patterns are available for a specific URL name (i.e. `kwargs_list` contains
        multiple entries), the generated annotation will be the union of the possible tuple shapes.

        Args:
            sequence_fallback: Whether to include a `Sequence[Any]` fallback type, to match against other
                sequence types such as lists.
        """
        args_lengths = [len(kwargs) for kwargs in self.kwargs_list]
        tuples_str = [
            f"tuple[{', '.join('SupportsStr' for _ in range(length))}]" for length in args_lengths if length > 0
        ]
        if 0 in args_lengths:
            tuples_str.extend(["tuple[()]", "None"])
        if sequence_fallback:
            tuples_str.append("Sequence[Any]")

        return " | ".join(tuples_str)


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
        return _get_reverse_map(get_resolver())

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
    url_resolver: URLResolver,
    parent_namespaces: list[str] | None = None,
) -> defaultdict[str, PathInfo]:
    parent_namespaces = parent_namespaces or []
    paths_info: defaultdict[str, PathInfo] = defaultdict(PathInfo)

    for pattern in reversed(url_resolver.url_patterns):  # Parsing in reverse is important!
        if isinstance(pattern, URLPattern) and pattern.name:
            key = ":".join(parent_namespaces)
            if key:
                key += ":"
            key += pattern.name

            reverse_entries = url_resolver.reverse_dict.getlist(pattern.name)

            for possibility, _, defaults, _ in reverse_entries:
                for _, params in possibility:
                    paths_info[key].add_kwargs_entry({k: (k not in defaults) for k in params})
        elif isinstance(pattern, URLResolver):
            new_parent_namespaces = parent_namespaces.copy()
            if pattern.namespace:
                new_parent_namespaces.append(pattern.namespace)

            paths_info = {**paths_info, **_get_reverse_map(pattern, new_parent_namespaces)}

    return paths_info
