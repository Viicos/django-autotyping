from typing import cast

import libcst as cst
import libcst.matchers as m
from libcst import helpers
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor

from django_autotyping.typing import ModelType

from .utils import get_method_node, get_model_alias, get_model_imports, get_param

OVERLOAD_DECORATOR = cst.Decorator(decorator=cst.Name("overload"))

# Matchers:

BASE_MANAGER_CLASS_DEF_MATCHER = m.ClassDef(name=m.Name("BaseManager"))
"""Matches the `ManyToManyField` class definition."""

T_TYPE_VAR_MATCHER = m.SimpleStatementLine(body=[m.Assign(targets=[m.AssignTarget(m.Name("_T"))])])
"""Matches the definition of the `_T` type variable."""


class QueryLookupsOverloadCodemod(VisitorBasedCodemodCommand):
    """A codemod that will add overloads to the `__init__` methods of related fields.

    Rule identifier: `DJAS002`.
    """

    STUB_FILES = {"db/models/manager.pyi"}

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.django_models = cast(list[ModelType], context.scratch["django_models"])

        model_imports = get_model_imports(self.django_models)

        # TODO LibCST should support adding imports from `ImportItem` objects
        imports = AddImportsVisitor._get_imports_from_context(context)
        imports.extend(model_imports)
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
        """Adds a `SimpleStatementLine` to define `_ModelT = TypeVar("_ModelT", bound=Model)`
        following the `_GT` type variable.
        """
        body = list(updated_node.body)

        model_typed_dicts = _build_model_kwargs(self.django_models)

        t_type_var = next(node for node in body if m.matches(node, T_TYPE_VAR_MATCHER))
        index = body.index(t_type_var) + 1
        body[index:index] = model_typed_dicts

        return updated_node.with_changes(
            body=body,
        )

    @m.leave(BASE_MANAGER_CLASS_DEF_MATCHER)
    def mutate_classDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        """Add the necessary overloads to foreign fields that supports
        that supports parametrization of the `__set__` and `__get__` types.
        """

        get_method = get_method_node(updated_node, "get")
        overload_get = get_method.with_changes(decorators=[OVERLOAD_DECORATOR])

        overloads: list[cst.FunctionDef] = []

        for model in self.django_models:
            # TODO This needs a proper Django Context object, instead of these utilities
            model_name = get_model_alias(model, self.django_models) or model.__name__

            # sets `self: ManyToManyField[model_name, _Through]`
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


def _build_model_kwargs(models: list[ModelType]) -> list[cst.ClassDef]:
    class_defs: list[cst.ClassDef] = []

    for model in models:
        model_name = get_model_alias(model, models) or model.__name__
        class_defs.append(
            cst.ClassDef(
                name=cst.Name(f"{model_name}Kwargs"),
                bases=[cst.Arg(cst.Name("TypedDict"))],
                keywords=[
                    cst.Arg(
                        keyword=cst.Name("total"),
                        equal=cst.AssignEqual(cst.SimpleWhitespace(""), cst.SimpleWhitespace("")),
                        value=cst.Name("False"),
                    )
                ],
                body=cst.IndentedBlock(
                    [
                        cst.SimpleStatementLine(
                            [cst.AnnAssign(target=cst.Name(field.name), annotation=cst.Annotation(cst.Name("Any")))]
                        )
                        for field in model._meta.get_fields()
                    ]
                ),
            )
        )

    return class_defs
