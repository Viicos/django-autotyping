from __future__ import annotations

import libcst as cst
import libcst.matchers as m
from libcst import helpers
from libcst.codemod import CodemodContext

from django_autotyping.typing import FlattenFunctionDef

from .base import StubVisitorBasedCodemod
from .constants import OVERLOAD_DECORATOR
from .utils import get_param

# Matchers:

CLASS_DEF_MATCHER = m.ClassDef(name=m.Name("Apps"))
"""Matches the `Apps` class definition."""

GET_MODEL_DEF_MATCHER = m.FunctionDef(name=m.Name("get_model"))
"""Matches the `get_model` method definition."""


class GetModelOverloadCodemod(StubVisitorBasedCodemod):
    """A codemod that will add overloads to the [`apps.get_model`][django.apps.apps.get_model] method.

    Rule identifier: `DJAS010`.

    ```python
    reveal_type(apps.get_model("app_name.ModelName"))  # Revealed type is type[ModelName]
    reveal_type(apps.get_model("app_name", "ModelName"))  # Revealed type is type[ModelName]
    ```
    """

    STUB_FILES = {"apps/registry.pyi"}

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.add_model_imports()

        # Even though these are most likely included, we import them for safety:
        self.add_typing_imports(["Literal", "overload"])

    @m.call_if_inside(CLASS_DEF_MATCHER)
    @m.leave(GET_MODEL_DEF_MATCHER)
    def mutate_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> FlattenFunctionDef:
        overload = updated_node.with_changes(decorators=[OVERLOAD_DECORATOR])
        overloads: list[cst.FunctionDef] = []

        for model in self.django_context.models:
            for use_shortcut in (True, False):
                model_name = self.django_context.get_model_name(model)
                app_label = model._meta.app_label

                # sets `app_label: Literal[...]`
                app_label_param = get_param(overload, "app_label")
                if use_shortcut:
                    annotation = helpers.parse_template_expression(f'Literal["{app_label}.{model.__name__}"]')
                else:
                    annotation = helpers.parse_template_expression(f'Literal["{app_label}"]')
                overload_ = overload.with_deep_changes(
                    old_node=app_label_param,
                    annotation=cst.Annotation(annotation),
                )

                # sets `model_name: Literal[...]`
                model_name_param = get_param(overload_, "model_name")
                if use_shortcut:
                    annotation = helpers.parse_template_expression("Literal[None]")
                else:
                    annotation = helpers.parse_template_expression(f'Literal["{model.__name__}"]')

                overload_ = overload_.with_deep_changes(
                    old_node=model_name_param,
                    annotation=cst.Annotation(annotation),
                    default=None if not use_shortcut else model_name_param.default,
                    equal=cst.MaybeSentinel.DEFAULT if not use_shortcut else model_name_param.equal,
                )

                # sets return value
                overload_ = overload_.with_changes(
                    # This time use the imported model name!
                    returns=cst.Annotation(helpers.parse_template_expression(f"type[{model_name}]"))
                )

                overloads.append(overload_)

        return cst.FlattenSentinel(overloads)
