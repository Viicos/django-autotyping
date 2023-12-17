from __future__ import annotations

from typing import Collection

import libcst as cst
from libcst import helpers
from libcst import matchers as m
from libcst.codemod.visitors import ImportItem

from django_autotyping.typing import ModelType


def get_method_node(class_node: cst.ClassDef, method_name: str) -> cst.FunctionDef:
    method_def = m.FunctionDef(name=m.Name(method_name))
    return helpers.ensure_type(
        next(node for node in class_node.body.body if m.matches(node, method_def)), cst.FunctionDef
    )


def is_duplicate_model(model_name: str, models: Collection[ModelType]) -> bool:
    return len([m for m in models if m.__name__ == model_name]) >= 2  # noqa: PLR2004


def get_model_alias(model: ModelType, models: Collection[ModelType]) -> str | None:
    # TODO Should be a snake_case to CamelCase converter
    return (
        f"{model._meta.app_label.capitalize()}{model.__name__}" if is_duplicate_model(model.__name__, models) else None
    )


def get_model_imports(models: Collection[ModelType]) -> list[ImportItem]:
    """Get a list of imports for the specified models.

    If one of the model's name clashes with another one, the import is aliased.
    """
    return [
        ImportItem(
            module_name=model._meta.app_config.models_module.__name__,
            obj_name=model.__name__,
            alias=get_model_alias(model, models),
        )
        for model in models
    ]


def get_param(node: cst.FunctionDef, param_name: str) -> cst.Param:
    return next(param for param in node.params.params if param.name.value == param_name)


def get_kw_param(node: cst.FunctionDef, param_name: str) -> cst.Param:
    return next(param for param in node.params.kwonly_params if param.name.value == param_name)
