from __future__ import annotations

from typing import TYPE_CHECKING, cast

import libcst as cst
import libcst.matchers as m
from django.db.models import Field
from libcst import helpers
from libcst.codemod import CodemodContext
from libcst.metadata import ScopeProvider

from django_autotyping.typing import FlattenFunctionDef

from .base import InsertAfterImportsVisitor, StubVisitorBasedCodemod
from .constants import OVERLOAD_DECORATOR
from .utils import TypedDictAttribute, build_typed_dict, get_param

if TYPE_CHECKING:
    from ..django_context import DjangoStubbingContext

# Matchers:

MANAGER_QS_CLASS_DEF_MATCHER = m.ClassDef(
    name=m.SaveMatchedNode(m.Name("BaseManager") | m.Name("_QuerySet"), "cls_name")
)
"""Matches the `BaseManager` and `_QuerySet` class definitions."""

MODEL_CLASS_DEF_MATCHER = m.ClassDef(name=m.SaveMatchedNode(m.Name("Model"), "cls_name"))
"""Matches the `Model` class definition."""


CREATE_DEF_MATCHER = m.FunctionDef(name=m.Name("create") | m.Name("acreate"))
"""Matches the `create` and `acreate` method definitions."""


INIT_DEF_MATCHER = m.FunctionDef(name=m.Name("__init__"))
"""Matches the `__init__` method definition."""


class CreateOverloadCodemod(StubVisitorBasedCodemod):
    """A codemod that will add overloads to methods creating an instance of a model.

    **Rule identifier**: `DJAS002`.

    **Related settings**:

    -[`MODEL_FIELDS_OPTIONAL`][django_autotyping.app_settings.StubsGenerationSettings.MODEL_FIELDS_OPTIONAL].

    ```python
    MyModel(...)  # Signature is provided.
    MyModel.objects.create(...)  # Signature is provided.
    ```

    ??? abstract "Implementation"
        This codemod makes use of the [PEP 692][pep-0692]. If your type checker/LSP supports it,
        documentation is provided for each field if [`help_text`][django.db.models.Field.help_text] was set.
    """

    METADATA_DEPENDENCIES = {ScopeProvider}
    STUB_FILES = {"db/models/manager.pyi", "db/models/query.pyi", "db/models/base.pyi"}

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.add_model_imports()
        model_typed_dicts = _build_model_kwargs(self.django_context, self.stubs_settings.MODEL_FIELDS_OPTIONAL)
        InsertAfterImportsVisitor.insert_after_imports(context, model_typed_dicts)

        # Even though these are most likely included, we import them for safety:
        self.add_typing_imports(["TypedDict", "TypeVar", "Unpack", "overload"])

    def mutate_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> FlattenFunctionDef:
        cls_name = self.get_metadata(ScopeProvider, original_node).name

        overload = updated_node.with_changes(decorators=[OVERLOAD_DECORATOR])
        overloads: list[cst.FunctionDef] = []

        for model in self.django_context.models:
            model_name = self.django_context.get_model_name(model)

            # sets `self: BaseManager[model_name]/_QuerySet[model_name, _Row]/model_name`
            if cls_name == "_QuerySet":
                annotation = helpers.parse_template_expression(f"{cls_name}[{model_name}, _Row]")
            elif cls_name == "BaseManager":
                annotation = helpers.parse_template_expression(f"{cls_name}[{model_name}]")
            else:
                annotation = helpers.parse_template_expression(model_name)
            self_param = get_param(overload, "self")
            overload_ = overload.with_deep_changes(
                old_node=self_param,
                annotation=cst.Annotation(annotation),
            )

            overload_ = overload_.with_deep_changes(
                old_node=overload_.params.star_kwarg,
                annotation=cst.Annotation(
                    annotation=helpers.parse_template_expression(f"Unpack[{model_name}CreateKwargs]")
                ),
            )

            if cls_name == "Model":
                # Remove `*args` from the definition:
                overload_ = overload_.with_deep_changes(
                    old_node=overload_.params,
                    star_arg=cst.MaybeSentinel.DEFAULT,
                )

            overloads.append(overload_)

        return cst.FlattenSentinel(overloads)

    @m.call_if_inside(MANAGER_QS_CLASS_DEF_MATCHER)
    @m.leave(CREATE_DEF_MATCHER)
    def mutate_create_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> FlattenFunctionDef:
        """Add overloads for `create`/`acreate` if in `BaseManager`/`_QuerSet`."""
        return self.mutate_FunctionDef(original_node, updated_node)

    @m.call_if_inside(MODEL_CLASS_DEF_MATCHER)
    @m.leave(INIT_DEF_MATCHER)
    def mutate_init_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> FlattenFunctionDef:
        """Add overloads for `__init__` if in `Model`."""
        return self.mutate_FunctionDef(original_node, updated_node)


def _build_model_kwargs(django_context: DjangoStubbingContext, all_optional: bool) -> list[cst.ClassDef]:
    class_defs: list[cst.ClassDef] = []

    for model in django_context.models:
        model_name = django_context.get_model_name(model)
        class_defs.append(
            build_typed_dict(
                f"{model_name}CreateKwargs",
                attributes=[
                    TypedDictAttribute(
                        field.name,
                        annotation="Any",
                        docstring=getattr(field, "help_text", None) or None,
                        required=not all_optional and not django_context.get_field_nullability(field),
                    )
                    for field in cast(list[Field], model._meta._get_fields(reverse=False))
                ],
                total=False,
                leading_line=True,
            )
        )

    return class_defs
