from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import LazySettings

from ._compat import Self
from .typing import AutotypingSettingsDict, RulesT


@dataclass
class CodeGenerationSettings:
    """Configuration for adding type annotations to Django user code."""

    PROJECT_DIR: Path | None = None
    """The directory of the project, where code modifications should be applied."""

    DIFF: bool = False
    """Show changes to be applied instead of modifying existing files."""

    TYPE_CHECKING_BLOCK: bool = True
    """Whether newly added imports should be in an `if TYPE_CHECKING` block (avoids circular imports)."""

    ASSUME_CLASS_GETITEM: bool = False
    """Whether generic classes in stubs files but not at runtime should be assumed to have a
    `__class_getitem__` method. This can be achieved by using `django-stubs-ext` or manually.

    Affected rules: `DJA001`.
    """


@dataclass
class StubsGenerationSettings:
    """Configuration for dynamic stubs generation."""

    LOCAL_STUBS_DIR: Path | None = None
    """The directory of the local type stubs. If not set, this setting must be set as a CLI argument."""

    SOURCE_STUBS_DIR: Path | None = None
    """The directory of the source `django-stubs` to be used. Will default
    to the first entry in site packages.
    """

    ALLOW_PLAIN_MODEL_REFERENCES: bool = True
    """Whether string references in the form of `{model_name}` should be generated in overloads.

    If set to `True`, both `{model_name}` and `{model_name}.{app_label}` are allowed
    (unless the model name has a duplicate in a different app).

    Affected rules: `DJAS001`.
    """

    ALLOW_NONE_SET_TYPE: bool = False
    """Whether to allow having the `__set__` type variable set to `None`, even if the field is not nullable.

    While Django allows setting most model instance fields to any value (before saving),
    it is generally a bad practice to do so. However, it might be beneficial to allow `None`
    to be set temporarly.

    This also works for foreign fields, where unlike standard fields, the Django descriptor used
    only allows model instances and `None` to be set.

    Affected rules: `DJAS001`.
    """

    MODEL_FIELDS_OPTIONAL: bool = True
    """Whether all model fields should be considered optional when creating model instances.

    This affects the following signatures:

    - [`Manager.create/acreate`][django.db.models.Manager]
    - `__init__` methods of models

    A lot can happen behind the scenes when instantiating models. Even if a field doesn't have
    a default value provided, the database could have triggers implemented that would provide one.
    This is why, by default, this configuration attribute defaults to `True`. If set to `False`,
    `django-autotyping` will try its best to determine required fields, namely by checking if:

    - the field can be [`null`][django.db.models.Field.null]
    - the field has a default or a database default value set
    - the field is a subclass of [`DateField`][django.db.models.DateField] and has
      [`auto_now`][django.db.models.DateField.auto_now] or [`auto_now_add`][django.db.models.DateField.auto_now_add]
      set to `True`.

    Affected rules: `DJAS002`.
    """

    ALLOW_REVERSE_ARGS: bool = False
    """Whether type checking should be added to the `args` argument of [`reverse`][django.urls.reverse].

    By default, this is set to `False` to avoid having too many overloads being generated.
    Moreover, only tuples can be type checked, and most people are using lists for this argument.
    Instead, it is recommended to use the `kwargs` argument.

    Affected rules: `DJAS011`.
    """


@dataclass
class AutotypingSettings:
    """A class holding the django-autotyping configuration."""

    IGNORE: list[RulesT] = field(default_factory=list)
    """A list of ignored rules."""

    STUBS_GENERATION: StubsGenerationSettings = field(default_factory=StubsGenerationSettings)
    """Stub related settings."""

    CODE_GENERATION: CodeGenerationSettings = field(default_factory=CodeGenerationSettings)
    """Code generation related settings."""

    @classmethod
    def from_django_settings(cls, settings: LazySettings) -> Self:
        # Not pretty, but we are limited by dataclasses
        autotyping_settings: AutotypingSettingsDict = deepcopy(getattr(settings, "AUTOTYPING", {}))
        stubs_generation_dct = autotyping_settings.pop("STUBS_GENERATION", {})
        code_generation_dct = autotyping_settings.pop("CODE_GENERATION", {})
        return cls(
            **autotyping_settings,
            STUBS_GENERATION=StubsGenerationSettings(**stubs_generation_dct),
            CODE_GENERATION=CodeGenerationSettings(**code_generation_dct),
        )
