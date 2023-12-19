from __future__ import annotations

from typing import TYPE_CHECKING, cast

import libcst as cst
import libcst.matchers as m
from libcst import helpers
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor

from .constants import OVERLOAD_DECORATOR
from .utils import TypedDictField, build_typed_dict, get_method_node, get_param

if TYPE_CHECKING:
    from ..django_context import DjangoStubbingContext
    from ..settings import StubSettings

# Matchers:

BASE_MANAGER_CLASS_DEF_MATCHER = m.ClassDef(name=m.Name("BaseManager"))
"""Matches the `ManyToManyField` class definition."""

T_TYPE_VAR_MATCHER = m.SimpleStatementLine(body=[m.Assign(targets=[m.AssignTarget(m.Name("_T"))])])
"""Matches the definition of the `_T` type variable."""


class CreateOverloadCodemod(VisitorBasedCodemodCommand):
    """A codemod that will add overloads to the `__init__` methods of related fields.

    Rule identifier: `DJAS003`.
    """

    STUB_FILES = {"db/models/manager.pyi"}

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.django_context = cast("DjangoStubbingContext", context.scratch["django_context"])
        self.stub_settings = cast("StubSettings", context.scratch["stub_settings"])

        # TODO LibCST should support adding imports from `ImportItem` objects
        imports = AddImportsVisitor._get_imports_from_context(context)
        imports.extend(self.django_context.model_imports)
        self.context.scratch[AddImportsVisitor.CONTEXT_KEY] = imports

        # Even though these are most likely included, we import them for safety:
        added_imports = [
            ("typing", "TypedDict"),
            ("typing", "TypeVar"),
            ("typing", "overload"),
            ("typing_extensions", "Unpack"),
        ]

        for added_import in added_imports:
            AddImportsVisitor.add_needed_import(
                self.context,
                module=added_import[0],
                obj=added_import[1],
            )

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Add the `TypedDict` declarations, used to type `kwargs` arguments of `create`."""
        body = list(updated_node.body)

        model_typed_dicts = _build_model_kwargs(self.django_context)

        t_type_var = next(node for node in body if m.matches(node, T_TYPE_VAR_MATCHER))
        index = body.index(t_type_var) + 1
        body[index:index] = model_typed_dicts

        return updated_node.with_changes(
            body=body,
        )

    @m.leave(BASE_MANAGER_CLASS_DEF_MATCHER)
    def mutate_classDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        """Add the necessary overloads to the `create` method of `BaseManager`."""

        get_method = get_method_node(updated_node, "get")
        overload_get = get_method.with_changes(decorators=[OVERLOAD_DECORATOR])

        overloads: list[cst.FunctionDef] = []

        for model in self.django_context.models:
            model_name = self.django_context.get_model_name(model)

            # sets `self: BaseManager[model_name]`
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
    class_defs: list[cst.ClassDef] = []

    for model in django_context.models:
        model_name = django_context.get_model_name(model)
        class_defs.append(
            build_typed_dict(
                f"{model_name}Kwargs",
                fields=[
                    TypedDictField(
                        field.name, annotation="Any", docstring=field.help_text or None, required=not field.null
                    )  # Or has default?
                    for field in model._meta.get_fields()
                ],
            )
        )

    return class_defs
