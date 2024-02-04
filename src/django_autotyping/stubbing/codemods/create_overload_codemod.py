from __future__ import annotations

import libcst as cst
import libcst.matchers as m
from libcst import helpers

from django_autotyping._compat import override
from django_autotyping.typing import FlattenFunctionDef

from ._model_creation import ModelCreationBaseCodemod

# Matchers:

MANAGER_QS_CLASS_DEF_MATCHER = m.ClassDef(
    name=m.SaveMatchedNode(m.Name("BaseManager") | m.Name("_QuerySet"), "cls_name")
)
"""Matches the `BaseManager` and `_QuerySet` class definitions."""


CREATE_DEF_MATCHER = m.FunctionDef(name=m.Name("create") | m.Name("acreate"))
"""Matches the `create` and `acreate` method definitions."""


class CreateOverloadCodemod(ModelCreationBaseCodemod):
    """A codemod that will add overloads to the [`create`][django.db.models.query.QuerySet.create]
    and [`acreate`][django.db.models.query.QuerySet.acreate] methods.

    **Rule identifier**: `DJAS002`.

    **Related settings**:

    - [`MODEL_FIELDS_OPTIONAL`][django_autotyping.app_settings.StubsGenerationSettings.MODEL_FIELDS_OPTIONAL].

    ```python
    MyModel.objects.create(...)  # Signature is provided.
    ```

    ??? abstract "Implementation"
        This codemod makes use of the [PEP 692][pep-0692]. If your type checker/LSP supports it,
        documentation is provided for each field if [`help_text`][django.db.models.Field.help_text] was set.
    """

    KWARGS_TYPED_DICT_NAME = "{model_name}CreateKwargs"
    STUB_FILES = {"db/models/manager.pyi", "db/models/query.pyi"}

    @override
    def get_self_annotation(self, model_name: str, class_name: str) -> cst.BaseExpression:
        if class_name == "_QuerySet":
            return helpers.parse_template_expression(f"{class_name}[{model_name}, _Row]")
        elif class_name == "BaseManager":
            return helpers.parse_template_expression(f"{class_name}[{model_name}]")

    @m.call_if_inside(MANAGER_QS_CLASS_DEF_MATCHER)
    @m.leave(CREATE_DEF_MATCHER)
    def mutate_create_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> FlattenFunctionDef:
        """Add overloads for `create`/`acreate` if in `BaseManager`/`_QuerSet`."""
        return self.mutate_FunctionDef(original_node, updated_node)
