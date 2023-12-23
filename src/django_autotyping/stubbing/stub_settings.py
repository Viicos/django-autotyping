from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from django.conf import LazySettings

from .codemods import RulesT


@dataclass
class StubSettings:
    """A class holding the configuration for stubs generation."""

    stubs_dir: Path
    """The directory pointing to local type stubs."""

    disabled_rules: list[RulesT] = field(default_factory=list)
    """A list of disabled rules."""

    allow_plain_model_references: bool = True
    """Whether string references in the form of `{model_name}` should be generated in overloads.

    If set to `True`, both `{model_name}` and `{model_name}.{app_label}` are allowed
    (unless the model name has a duplicate in a different app).

    Affected rules: `DJAS001`.
    """

    allow_none_set_type: bool = False
    """Whether to allow having the `__set__` type variable set to `None`.

    While Django allows setting most model instance fields to any value (before saving),
    it is generally a bad practice to do so. However, it might be beneficial to allow `None`
    to be set temporarly.

    This also works for foreign fields, where unlike standard fields, the Django descriptor used
    only allows model instances and `None` to be set.

    Affected rules: `DJAS001`.
    """

    model_fields_optional: bool = True
    """Whether all model fields should be considered optional when creating model instances.

    This affects the following signatures:
    - `Manager.create/acreate`
    - `__init__` methods of models

    A lot can happen behind the scenes when instantiating models. Even if a field doesn't have
    a default value provided, the database could have triggers implemented that would provide one.
    This is why, by default, this configuration attribute defaults to `True`. If set to `False`,
    `django-autotyping` will try its best to determine required fields, namely by checking if:
    - the field can be `null`
    - the field has a default or a database default value set
    - the field is a subclass of `DateField` and has `auto_now` or `auto_now_add` set to `True`.

    Affected rules: `DJAS002`.
    """

    @classmethod
    def from_django_settings(cls, settings: LazySettings):
        autotyping_settings: dict[str, Any] = getattr(settings, "AUTOTYPING", {})

        return cls(**{k.lower(): v for k, v in autotyping_settings.items()})
