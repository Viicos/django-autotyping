from __future__ import annotations

from typing import TYPE_CHECKING

import libcst as cst
import libcst.matchers as m
from libcst import helpers
from libcst.codemod import CodemodContext

from .base import StubVisitorBasedCodemod
from .constants import OVERLOAD_DECORATOR
from .utils import TypedDictField, build_typed_dict, get_method_node, get_param

if TYPE_CHECKING:
    from ..django_context import DjangoStubbingContext

# Matchers:

BASE_MANAGER_CLASS_DEF_MATCHER = m.ClassDef(name=m.Name("BaseManager"))
"""Matches the `ManyToManyField` class definition."""


class QueryLookupsOverloadCodemod(StubVisitorBasedCodemod):
    """A codemod that will add overloads to the `__init__` methods of related fields.

    Rule identifier: `DJAS003`.
    """

    STUB_FILES = {"db/models/manager.pyi"}

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.add_model_imports()

        # Even though these are most likely included, we import them for safety:
        self.add_typing_imports(["TypedDict", "TypeVar", "Unpack", "overload"])

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Add the necessary `TypedDict` definitions after imports."""
        model_typed_dicts = _build_model_kwargs(self.django_context.models)
        return self.insert_after_imports(updated_node, model_typed_dicts)

    @m.leave(BASE_MANAGER_CLASS_DEF_MATCHER)
    def mutate_classDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        """Add the necessary overloads to foreign fields that supports
        that supports parametrization of the `__set__` and `__get__` types.
        """

        get_method = get_method_node(updated_node, "get")
        overload_get = get_method.with_changes(decorators=[OVERLOAD_DECORATOR])

        overloads: list[cst.FunctionDef] = []

        for model in self.django_context.models:
            model_name = self.django_context.get_model_name(model)

            # sets `self: ManyToManyField[model_name, _Through]`
            self_param = get_param(overload_get, "self")
            overload = overload_get.with_deep_changes(
                old_node=self_param,
                annotation=cst.Annotation(annotation=helpers.parse_template_expression(f"BaseManager[{model_name}]")),
            )

            overload = overload.with_deep_changes(
                old_node=overload.params.star_kwarg,
                annotation=cst.Annotation(annotation=helpers.parse_template_expression(f"Unpack[{model_name}Kwargs]")),
            )

            overloads.append(overload)

        new_body = list(updated_node.body.body)
        get_index = new_body.index(get_method)
        new_body.pop(get_index)

        new_body[get_index:get_index] = overloads

        return updated_node.with_deep_changes(old_node=updated_node.body, body=new_body)


def _build_model_kwargs(django_context: DjangoStubbingContext) -> list[cst.ClassDef]:
    # TODO This needs to build the available lookups
    class_defs: list[cst.ClassDef] = []

    for model in django_context.models:
        model_name = django_context.get_model_name(model)
        class_defs.append(
            build_typed_dict(
                f"{model_name}CreateKwargs",
                fields=[
                    TypedDictField(
                        field.name,
                        annotation="Any",
                        docstring=getattr(field, "help_text", None) or None,
                    )
                    for field in model._meta._get_fields(reverse=False)
                ],
                total=False,  # TODO find a way to determine which fields are required.
                leading_line=True,
            )
        )

    return class_defs
