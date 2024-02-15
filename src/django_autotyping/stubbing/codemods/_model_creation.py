from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, TypedDict, cast

import libcst as cst
from django.db.models import (
    AutoField,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    DecimalField,
    Field,
    FloatField,
    GenericIPAddressField,
    IntegerField,
    IPAddressField,
    TextField,
    TimeField,
    UUIDField,
)
from django.db.models.fields.reverse_related import ForeignObjectRel
from libcst import helpers
from libcst.codemod import CodemodContext
from libcst.codemod.visitors import AddImportsVisitor, ImportItem
from libcst.metadata import ScopeProvider

from django_autotyping._compat import Required
from django_autotyping.typing import FlattenFunctionDef

from ._utils import TypedDictAttribute, build_typed_dict, get_param
from .base import InsertAfterImportsVisitor, StubVisitorBasedCodemod
from .constants import OVERLOAD_DECORATOR


class FieldType(TypedDict):
    type: Required[str]
    """The stringified type annotation to be used."""

    typing_imports: list[str]
    """A list of typing objects to be imported."""

    extra_imports: list[ImportItem]
    """A list of extra import items to be included."""


# This types are taken from `django-stubs`
# NOTE: Order matters! This dict is iterated in order to match field classes
# against the keys. Be sure to define the most specific subclasses first
# (e.g. `AutoField` is a subclass of `IntegerField`, so it is defined first).
# NOTE: Maybe `get_args(field_instance.__orig_class__)` could be used to take into
# account explicit parametrization.
FIELD_SET_TYPES_MAP: dict[type[Field], FieldType] = {
    AutoField: {
        "type": "int | str | Combinable",
    },
    IntegerField: {"type": "float | int | str | Combinable"},
    FloatField: {"type": "float | int | str | Combinable"},
    DecimalField: {"type": "str | float | Decimal | Combinable", "extra_imports": [ImportItem("decimal", "Decimal")]},
    CharField: {"type": "str | int | Combinable"},  # TODO this and textfield seems to allow `SupportsStr`
    TextField: {"type": "str | Combinable"},
    BooleanField: {"type": "bool | Combinable"},
    IPAddressField: {"type": "str | Combinable"},
    GenericIPAddressField: {
        "type": "str | int | Callable[..., Any] | Combinable",  # TODO, Callable, really?
        "typing_imports": ["Any", "Callable"],
    },
    # For datetime related fields, we use `datetime.x` because `datetime`
    # is already imported in `db/models/manager.pyi`:
    DateTimeField: {
        "type": "str | datetime.datetime | datetime.Date | Combinable",
        "extra_imports": [ImportItem("datetime")],
    },
    DateField: {
        "type": "str | datetime.date | Combinable",
        "extra_imports": [ImportItem("datetime")],
    },
    TimeField: {
        "type": "str | datetime.time | datetime.datetime | Combinable",
        "extra_imports": [ImportItem("datetime")],
    },
    UUIDField: {"type": "str | UUID", "extra_imports": [ImportItem("uuid", "UUID")]},
    Field: {"type": "Any", "typing_imports": ["Any"]},
}
"""A mapping of field classes to the types they allow to be set to."""


class ModelCreationBaseCodemod(StubVisitorBasedCodemod, ABC):
    """A base codemod that can be used to add overloads for model creation.

    Useful for: `Model.__init__`, `BaseManager.create`.
    """

    METADATA_DEPENDENCIES = {ScopeProvider}
    KWARGS_TYPED_DICT_NAME: ClassVar[str]
    """A templated string to render the name of the `TypedDict` for the `**kwargs` annotation.

    Should contain the template `{model_name}`.
    """

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.add_model_imports()

        model_typed_dicts = self.build_model_kwargs()
        InsertAfterImportsVisitor.insert_after_imports(context, model_typed_dicts)

        AddImportsVisitor.add_needed_import(
            self.context,
            module="django.db.models.expressions",
            obj="Combinable",
        )

        # Even though most of them are likely included, we import them for safety:
        self.add_typing_imports(["TypedDict", "TypeVar", "Required", "Unpack", "overload"])

    def build_model_kwargs(self) -> list[cst.ClassDef]:
        """Return a list of class definition representing the typed dicts to be used for overloads."""

        contenttypes_installed = self.django_context.apps.is_installed("django.contrib.contenttypes")
        if contenttypes_installed:
            from django.contrib.contenttypes.fields import GenericForeignKey
        all_optional = self.stubs_settings.MODEL_FIELDS_OPTIONAL

        class_defs: list[cst.ClassDef] = []

        for model in self.django_context.models:
            model_name = self.django_context.get_model_name(model)

            # This mostly follows the implementation of the Django's `Model.__init__` method:
            typed_dict_attributes = []
            for field in cast(list[Field], model._meta.fields):
                if isinstance(field.remote_field, ForeignObjectRel):
                    # TODO support for attname as well (i.e. my_foreign_field_id).
                    # Issue is if this is a required field, we can't make both required at the same time
                    attr_name = field.name
                    if isinstance(field.remote_field.model, str):
                        # This seems to happen when a string reference can't be resolved
                        # It should be invalid at runtime but let's not error here.
                        annotation = "Any"
                        self.add_typing_imports(["Any"])
                    else:
                        annotation = self.django_context.get_model_name(
                            # As per `ForwardManyToOneDescriptor.__set__`:
                            field.remote_field.model._meta.concrete_model
                        )
                        annotation += " | Combinable"
                elif contenttypes_installed and isinstance(field, GenericForeignKey):
                    # it's generic, so cannot set specific model
                    attr_name = field.name
                    annotation = "Any"
                    self.add_typing_imports(["Any"])
                else:
                    attr_name = field.attname
                    # Regular fields:
                    field_set_type = next(
                        (v for k, v in FIELD_SET_TYPES_MAP.items() if issubclass(type(field), k)),
                        FieldType(type="Any", typing_imports=["Any"]),
                    )

                    self.add_typing_imports(field_set_type.get("typing_imports", []))
                    if extra_imports := field_set_type.get("extra_imports"):
                        imports = AddImportsVisitor._get_imports_from_context(self.context)
                        imports.extend(extra_imports)
                        self.context.scratch[AddImportsVisitor.CONTEXT_KEY] = imports

                    annotation = field_set_type["type"]

                if not isinstance(field, GenericForeignKey) and self.django_context.is_nullable_field(field):
                    annotation += " | None"

                typed_dict_attributes.append(
                    TypedDictAttribute(
                        attr_name,
                        annotation=annotation,
                        docstring=getattr(field, "help_text", None) or None,
                        required=not all_optional and self.django_context.is_required_field(field),
                    )
                )

            class_defs.append(
                build_typed_dict(
                    self.KWARGS_TYPED_DICT_NAME.format(model_name=model_name),
                    attributes=typed_dict_attributes,
                    total=False,
                    leading_line=True,
                )
            )

        return class_defs

    def mutate_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> FlattenFunctionDef:
        class_name = self.get_metadata(ScopeProvider, original_node).name

        overload = updated_node.with_changes(decorators=[OVERLOAD_DECORATOR])
        overloads: list[cst.FunctionDef] = []

        for model in self.django_context.models:
            model_name = self.django_context.get_model_name(model)

            # sets `self: BaseManager[model_name]/_QuerySet[model_name, _Row]/model_name`
            annotation = self.get_self_annotation(model_name, class_name)
            self_param = get_param(overload, "self")
            overload_ = overload.with_deep_changes(
                old_node=self_param,
                annotation=cst.Annotation(annotation),
            )

            overload_ = overload_.with_deep_changes(
                old_node=overload_.params.star_kwarg,
                annotation=cst.Annotation(
                    annotation=helpers.parse_template_expression(
                        f"Unpack[{self.KWARGS_TYPED_DICT_NAME}]".format(model_name=model_name)
                    )
                ),
            )

            overloads.append(overload_)

        return cst.FlattenSentinel(overloads)

    @abstractmethod
    def get_self_annotation(self, model_name: str, class_name: str) -> cst.BaseExpression:
        """Return the annotation to be set on the `self` parameter."""
