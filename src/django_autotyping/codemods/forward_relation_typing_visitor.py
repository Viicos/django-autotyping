from __future__ import annotations

import libcst as cst
import libcst.matchers as m
from django.db.models.fields.related import RECURSIVE_RELATIONSHIP_CONSTANT
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor
from libcst.metadata import ScopeProvider
from libcst.metadata.scope_provider import ClassScope

from ..models import ModelInfo

ASSIGN_FOREIGN_FIELD = m.Assign(
    value=m.Call(
        args=m.OneOf(
            (  # String reference as a kw: Field(to="Model"):
                m.ZeroOrMore(),
                m.Arg(value=m.SaveMatchedNode(m.SimpleString(), "string_reference"), keyword=m.Name("to")),
                m.ZeroOrMore(),
            ),
            (  # String reference as the first positional arg: Field("Model"):
                m.Arg(value=m.SaveMatchedNode(m.SimpleString(), "string_reference"), keyword=None),
                m.ZeroOrMore(),
            ),
        )
    )
)


class ForwardRelationTypingVisitor(VisitorBasedCodemodCommand):
    """A visitor that will add type annotations to forward relations.

    Rule identifier: `DJA001`.

    ```python
    from typing import TYPE_CHECKING

    from django.db import models

    # Model is imported in an `if TYPE_CHECKING` block if `--type-checking-block` is used.
    if TYPE_CHECKING:
        # Related model is imported from the corresponding apps models module:
        from myproject.reporters.models import Reporter


    class Article(models.Model):
        # If the field supports `__class_getitem__` at runtime, it is parametrized directly:
        reporter = models.ForeignKey["Reporter"](
            "reporters.Reporter",
            on_delete=models.CASCADE,
        )

        # Otherwise, an explicit annotation is used. No unnecessary import if model is in the same file.
        article_version: "models.OneToOneField[ArticleVersion]" = models.OneToOneField(
            "ArticleVersion",
            on_delete=models.CASCADE,
        )
    ```
    """

    METADATA_DEPENDENCIES = {ScopeProvider}

    def __init__(self, context: CodemodContext, model_infos: list[ModelInfo]) -> None:
        super().__init__(context)
        self.model_infos = model_infos
        self.current_model: ModelInfo | None = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool | None:
        scope = self.get_metadata(ScopeProvider, node)
        if type(scope) is ClassScope or not node.bases:  # TODO check for `object` base as well
            return False
        self.current_model = self.get_model_info(node)

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        self.current_model = None
        return updated_node

    @m.leave(ASSIGN_FOREIGN_FIELD)
    def type_any_to_one_field(self, original_node: cst.Assign, updated_node: cst.Assign) -> cst.Assign | cst.AnnAssign:
        if self.current_model is None:
            return updated_node

        # TODO handle multiple targets? Unlikely in the context of a Django model
        target = updated_node.targets[0].target
        forward_relation = self.current_model.forward_relations.get(target.value)
        if forward_relation is None:
            return updated_node

        extracted = m.extract(updated_node, ASSIGN_FOREIGN_FIELD)
        string_reference: cst.SimpleString = extracted.get("string_reference")
        if not string_reference:
            return updated_node

        splitted = string_reference.raw_value.split(".")
        if len(splitted) == 1:
            # reference is in the same app
            class_ref = splitted[0]
        else:
            # reference is from an outside app, e.g. myapp.MyModel
            class_ref = splitted[1]
        if class_ref == RECURSIVE_RELATIONSHIP_CONSTANT:
            # Handle relationships with itself
            class_ref = self.current_model.class_name

        # TODO Run a transformer to move in an `if TYPE_CHECKING` block.
        if self.current_model.module is not forward_relation.model_module:
            # TODO check if model is from the same app: do relative import
            if self.current_model.app_config is forward_relation.app_config:
                pass
            else:
                AddImportsVisitor.add_needed_import(
                    self.context,
                    module=forward_relation.app_models_module.__name__,
                    obj=class_ref,
                )

        if forward_relation.has_init_subclass:
            # We can parametrize the field directly, we won't get runtime TypeErrors
            annotation_str = f'["{class_ref}"]'  # forward ref used here as it will be evaluated at runtime
            if isinstance(updated_node.value.func, cst.Name):
                # e.g. `field = ForeignKey(...)`
                updated_node.value.func.value += annotation_str
            else:
                # e.g. `field = models.ForeignKey(...)`
                updated_node.value.func.attr.value += annotation_str
            return updated_node
        else:
            # We explicitly annotate to avoid runtime TypeErrors
            # e.g. from `field = ForeignKey(...)` to `field: ForeignKey[...] = ForeignKey(...)`
            annotation_str = f"{_get_attribute_path(updated_node.value.func)}[{class_ref}]"
            return cst.AnnAssign(
                target=target,
                annotation=cst.Annotation(annotation=cst.SimpleString(value=f'"{annotation_str}"')),
                value=updated_node.value,
            )

    def get_model_info(self, node: cst.ClassDef) -> ModelInfo | None:
        # TODO use a provider instead?
        return next((model_info for model_info in self.model_infos if model_info.class_name == node.name.value), None)


def _get_attribute_path(node: cst.Name | cst.Attribute) -> str:
    """Get the dotted path to an object from the `cst.Call.func` attribute.

    `node` can either be a `cst.Name` or a `cst.Attribute` node, meaning both use cases are supported:

    ```py
    field_1 = ForeignKey(...)  # Returns 'ForeignKey'
    field_2 = models.ForeignKey(...)  # Returns 'models.ForeignKey'
    ```
    """
    if isinstance(node, cst.Name):
        return node.value

    if isinstance(node.value, cst.Attribute):
        prefix = _get_attribute_path(node.value)
        print("prefix", prefix)
    else:
        prefix = node.value.value
    return f"{prefix}.{node.attr.value}"
