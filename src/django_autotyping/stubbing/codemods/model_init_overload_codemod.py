from __future__ import annotations

import libcst as cst
import libcst.matchers as m
from libcst import helpers
from libcst.codemod import CodemodContext

from django_autotyping._compat import override
from django_autotyping.typing import FlattenFunctionDef

from ._model_creation import ModelCreationBaseCodemod
from .base import InsertAfterImportsVisitor

# Matchers:

MODEL_CLASS_DEF_MATCHER = m.ClassDef(name=m.SaveMatchedNode(m.Name("Model"), "cls_name"))
"""Matches the `Model` class definition."""

INIT_DEF_MATCHER = m.FunctionDef(name=m.Name("__init__"))
"""Matches the `__init__` method definition."""


class ModelInitOverloadCodemod(ModelCreationBaseCodemod):
    """A codemod that will add overloads to the [`Model.__init__`][django.db.models.Model] method.

    **Rule identifier**: `DJAS003`.

    **Related settings**:

    - [`MODEL_FIELDS_OPTIONAL`][django_autotyping.app_settings.StubsGenerationSettings.MODEL_FIELDS_OPTIONAL].

    ```python
    MyModel(...)  # Signature is provided.
    ```

    ??? abstract "Implementation"
        This codemod makes use of the [PEP 692][pep-0692]. If your type checker/LSP supports it,
        documentation is provided for each field if [`help_text`][django.db.models.Field.help_text] was set.
    """

    KWARGS_TYPED_DICT_NAME = "{model_name}InitKwargs"
    STUB_FILES = {"db/models/base.pyi"}

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.add_model_imports()
        model_typed_dicts = self.build_model_kwargs()
        InsertAfterImportsVisitor.insert_after_imports(context, model_typed_dicts)

        # Even though these are most likely included, we import them for safety:
        self.add_typing_imports(["TypedDict", "TypeVar", "Unpack", "overload"])

    @override
    def mutate_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> FlattenFunctionDef:
        overloads = super().mutate_FunctionDef(original_node, updated_node)
        # Remove `*args` from the definition:
        return cst.FlattenSentinel(
            overload.with_deep_changes(old_node=overload.params, star_arg=cst.MaybeSentinel.DEFAULT)
            for overload in overloads.nodes
        )

    @override
    def get_self_annotation(self, model_name: str, class_name: str) -> cst.BaseExpression:
        return helpers.parse_template_expression(model_name)

    @m.call_if_inside(MODEL_CLASS_DEF_MATCHER)
    @m.leave(INIT_DEF_MATCHER)
    def mutate_init_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> FlattenFunctionDef:
        """Add overloads for `__init__` if in `Model`."""
        return self.mutate_FunctionDef(original_node, updated_node)
