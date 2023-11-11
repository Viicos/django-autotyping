from __future__ import annotations

import libcst as cst
import libcst.matchers as m
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand
from libcst.metadata import FullyQualifiedNameProvider, ScopeProvider
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


class AnyToOneTypingVisitor(VisitorBasedCodemodCommand):
    METADATA_DEPENDENCIES = {FullyQualifiedNameProvider, ScopeProvider}

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

        forward_relations = self.current_model.forward_relations
        target = updated_node.targets[0].target
        if forward_relation := forward_relations.get(target.value):
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

            # TODO Add import to model, in an `if TYPE_CHECKING` block.
            # This will require some additional info: in particular the `AppConfig.models_module`

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
