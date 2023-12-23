from __future__ import annotations

from typing import TYPE_CHECKING, cast

import libcst as cst
import libcst.matchers as m
from django.db.models import Field
from libcst import helpers
from libcst.codemod import CodemodContext

from .base import StubVisitorBasedCodemod
from .constants import OVERLOAD_DECORATOR
from .utils import TypedDictField, build_typed_dict, get_method_node, get_param

if TYPE_CHECKING:
    from ..django_context import DjangoStubbingContext

# Matchers:

CLASS_DEF_MATCHER = m.ClassDef(
    name=m.SaveMatchedNode(m.Name("BaseManager") | m.Name("_QuerySet") | m.Name("Model"), "cls_name")
)
"""Matches the `BaseManager` and `_QuerySet` class definitions."""


class CreateOverloadCodemod(StubVisitorBasedCodemod):
    """A codemod that will add overloads to methods creating an instance of a model.

    Rule identifier: `DJAS002`.
    """

    STUB_FILES = {"db/models/manager.pyi", "db/models/query.pyi", "db/models/base.pyi"}

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.add_model_imports()

        # Even though these are most likely included, we import them for safety:
        self.add_typing_imports(["TypedDict", "TypeVar", "Unpack", "overload"])

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Add the necessary `TypedDict` definitions after imports."""
        model_typed_dicts = _build_model_kwargs(self.django_context, self.stub_settings.all_model_fields_optional)
        return self.insert_after_imports(updated_node, model_typed_dicts)

    @m.leave(CLASS_DEF_MATCHER)
    def mutate_classDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        """Add the necessary overloads to the `create`/`acreate` methods of `BaseManager` and `_QuerSet`."""

        extracted = m.extract(updated_node, CLASS_DEF_MATCHER)
        cls_name: str = extracted.get("cls_name").value

        new_body = list(updated_node.body.body)

        method_names = ("__init__",) if cls_name == "Model" else ("create", "acreate")
        for method_name in method_names:
            create_method = get_method_node(updated_node, method_name)
            overload_create = create_method.with_changes(decorators=[OVERLOAD_DECORATOR])

            overloads: list[cst.FunctionDef] = []

            for model in self.django_context.models:
                model_name = self.django_context.get_model_name(model)

                # sets `self: BaseManager/_QuerySet[model_name]/model_name`
                if cls_name == "_QuerySet":
                    annotation = helpers.parse_template_expression(f"{cls_name}[{model_name}, _Row]")
                elif cls_name == "BaseManager":
                    annotation = helpers.parse_template_expression(f"{cls_name}[{model_name}]")
                else:
                    annotation = helpers.parse_template_expression(model_name)
                self_param = get_param(overload_create, "self")
                overload = overload_create.with_deep_changes(
                    old_node=self_param,
                    annotation=cst.Annotation(annotation),
                )

                overload = overload.with_deep_changes(
                    old_node=overload.params.star_kwarg,
                    annotation=cst.Annotation(
                        annotation=helpers.parse_template_expression(f"Unpack[{model_name}CreateKwargs]")
                    ),
                )

                if cls_name == "Model":
                    # Remove `*args` from the definition:
                    overload = overload.with_deep_changes(
                        old_node=overload.params,
                        star_arg=cst.MaybeSentinel.DEFAULT,
                    )

                overloads.append(overload)

            create_index = new_body.index(create_method)
            new_body.pop(create_index)

            new_body[create_index:create_index] = overloads

        return updated_node.with_deep_changes(old_node=updated_node.body, body=new_body)


def _build_model_kwargs(django_context: DjangoStubbingContext, all_optional: bool) -> list[cst.ClassDef]:
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
                        required=not all_optional and not django_context.is_optional(field),
                    )
                    for field in cast(list[Field], model._meta._get_fields(reverse=False))
                ],
                total=False,
                leading_line=True,
            )
        )

    return class_defs
