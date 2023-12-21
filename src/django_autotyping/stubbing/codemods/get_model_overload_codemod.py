from __future__ import annotations

import libcst as cst
import libcst.matchers as m
from libcst import helpers
from libcst.codemod import CodemodContext

from .base import StubVisitorBasedCodemod
from .constants import OVERLOAD_DECORATOR
from .utils import get_method_node, get_param

# Matchers:

CLASS_DEF_MATCHER = m.ClassDef(name=m.Name("Apps"))
"""Matches the `Apps` class definition."""


class GetModelOverloadCodemod(StubVisitorBasedCodemod):
    """A codemod that will add overloads to the `apps.get_model` method.

    Rule identifier: `DJAS010`.
    """

    STUB_FILES = {"apps/registry.pyi"}

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.add_model_imports()

        # Even though these are most likely included, we import them for safety:
        self.add_typing_imports(["Literal", "overload"])

    @m.leave(CLASS_DEF_MATCHER)
    def mutate_classDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        """Add the necessary overloads to the `create`/`acreate` methods of `BaseManager` and `_QuerSet`."""

        get_models_method = get_method_node(updated_node, "get_model")
        overload_get_model = get_models_method.with_changes(decorators=[OVERLOAD_DECORATOR])

        overloads: list[cst.FunctionDef] = []

        for model in self.django_context.models:
            for use_shortcut in (True, False):
                model_name = self.django_context.get_model_name(model)
                app_label = model._meta.app_label

                # sets `app_label: Literal[...]`
                app_label_param = get_param(overload_get_model, "app_label")
                if use_shortcut:
                    annotation = helpers.parse_template_expression(f'Literal["{app_label}.{model.__name__}"]')
                else:
                    annotation = helpers.parse_template_expression(f'Literal["{app_label}"]')
                overload = overload_get_model.with_deep_changes(
                    old_node=app_label_param,
                    annotation=cst.Annotation(annotation),
                )

                # sets `model_name: Literal[...]`
                model_name_param = get_param(overload, "model_name")
                if use_shortcut:
                    annotation = helpers.parse_template_expression("Literal[None]")
                else:
                    annotation = helpers.parse_template_expression(f'Literal["{model.__name__}"]')

                overload = overload.with_deep_changes(
                    old_node=model_name_param,
                    annotation=cst.Annotation(annotation),
                    default=None if not use_shortcut else model_name_param.default,
                    equal=cst.MaybeSentinel.DEFAULT if not use_shortcut else model_name_param.equal,
                )

                # sets return value
                overload = overload.with_changes(
                    # This time use the imported model name!
                    returns=cst.Annotation(helpers.parse_template_expression(f"type[{model_name}]"))
                )

                overloads.append(overload)

        new_body = list(updated_node.body.body)
        get_models_index = new_body.index(get_models_method)
        new_body.pop(get_models_index)

        new_body[get_models_index:get_models_index] = overloads

        return updated_node.with_deep_changes(old_node=updated_node.body, body=new_body)
