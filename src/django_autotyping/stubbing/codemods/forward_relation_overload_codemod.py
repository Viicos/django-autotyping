from typing import cast

import libcst as cst
import libcst.matchers as m
from libcst import helpers
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor

from django_autotyping.typing import ModelType

OVERLOAD_DECORATOR = cst.Decorator(decorator=cst.Name("overload"))

MODEL_T_TYPE_VAR = helpers.parse_template_statement('_ModelT = TypeVar("_ModelT", bound=Model)')
"""A statement assigning `_ModelT = TypeVar("_ModelT", bound=Model)`."""

# Matchers:

RELATED_CLASS_DEF_MATCHER = m.ClassDef(
    name=m.SaveMatchedNode(m.Name("ForeignObject") | m.Name("ForeignKey") | m.Name("OneToOneField"), "field_cls_name"),
)
"""Matches all foreign field class definitions that supports parametrization of the `__set__` and `__get__` types."""

INIT_METHOD_MATCHER = m.FunctionDef(name=m.Name("__init__"))
"""Matches all `__init__` methods."""

GET_TYPE_VAR_MATCHER = m.SimpleStatementLine(body=[m.Assign(targets=[m.AssignTarget(m.Name("_GT"))])])
"""Matches the definition of the `_GT` type variable."""


class ForwardRelationOverloadCodemod(VisitorBasedCodemodCommand):
    """A codemod that will add overloads to the `__init__` methods of related fields.

    Rule identifier: `DJAS001`.

    This codemod is meant to be applied on the `django-stubs/db/models/fields/related.pyi` stub file.

    ```python
    class ForeignKey(ForeignObject[_ST, _GT]):
        # For each model, will add two overloads:
        # - 1st: `null: Literal[True]`, which will set parametrize `ForeignKey` set/get types as `Optional`.
        # - 2nd: `null: Literal[False] = ...` (the default).
        # `to` is annotated as a `Literal`, with two values: {app_label}.{model_name} and {model_name}.
        @overload
        def __init__(
            self: ForeignKey[MyModel | <pk_type> | None, MyModel | None],
            to: Literal["MyModel", "myapp.MyModel"],
            ...
        ) -> None: ...
    ```
    """

    STUB_FILES = {"db/models/fields/related.pyi"}

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.django_models = cast(list[ModelType], context.scratch["django_models"])

        added_imports = [
            (model._meta.app_config.models_module.__name__, model.__name__) for model in self.django_models
        ]

        # Even though these are most likely included, we import them for safety:
        added_imports += [
            ("typing", "Literal"),
            ("typing", "TypeVar"),
            ("typing", "overload"),
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

        # TODO return if already exists? Depends if we play it smart and we don't rewrite the whole file each time

        gt_type_var = next(node for node in body if m.matches(node, GET_TYPE_VAR_MATCHER))
        body.insert(body.index(gt_type_var) + 1, MODEL_T_TYPE_VAR)

        return updated_node.with_changes(
            body=body,
        )

    @m.leave(RELATED_CLASS_DEF_MATCHER)
    def mutate_classDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        extracted = m.extract(updated_node, RELATED_CLASS_DEF_MATCHER)
        field_cls_name: str = extracted.get("field_cls_name").value

        init_node: cst.FunctionDef = next(
            node for node in updated_node.body.body if m.matches(node, INIT_METHOD_MATCHER)
        )

        overloads: list[cst.FunctionDef] = []

        # For each model, create two overloads, depending on the `null` valu:
        for model in self.django_models:
            for nullable in (True, False):  # Order matters!
                overload = init_node.with_changes(decorators=[OVERLOAD_DECORATOR])

                # sets `self: FieldName[<set_type>, <get_type>]`
                self_param = next(param for param in overload.params.params if param.name.value == "self")
                overload = overload.with_deep_changes(
                    old_node=self_param,
                    annotation=_build_self_annotation(field_cls_name, model.__name__, nullable),
                )

                # sets `to: Literal["model_name", "app_label.model_name"]`
                to_param = next(param for param in overload.params.params if param.name.value == "to")
                overload = overload.with_deep_changes(
                    old_node=to_param,
                    annotation=cst.Annotation(
                        annotation=cst.Subscript(
                            value=cst.Name("Literal"),
                            slice=[
                                cst.SubscriptElement(cst.Index(cst.SimpleString(f'"{model.__name__}"'))),
                                cst.SubscriptElement(
                                    cst.Index(cst.SimpleString(f'"{model._meta.app_label}.{model.__name__}"'))
                                ),
                            ],
                        )
                    ),
                )

                # sets `null: Literal[True/False]` (with the default removed accordingly)
                null_param = next(param for param in overload.params.kwonly_params if param.name.value == "null")
                overload = overload.with_deep_changes(
                    old_node=null_param,
                    annotation=cst.Annotation(
                        annotation=cst.Subscript(
                            value=cst.Name("Literal"), slice=[cst.SubscriptElement(cst.Index(cst.Name(str(nullable))))]
                        )
                    ),
                    default=None if nullable else null_param.default,  # Remove default to have a correct overload match
                    equal=cst.MaybeSentinel.DEFAULT if nullable else null_param.equal,
                )

                overloads.append(overload)

        # Now, handle the last overload, matching against a real model type:

        model_overload = init_node.with_changes(decorators=[OVERLOAD_DECORATOR])

        # sets `to: type[_ModelT]`, the type variable will be used to annotate `self` as well
        to_param = next(param for param in model_overload.params.params if param.name.value == "to")
        model_overload = model_overload.with_deep_changes(
            old_node=to_param,
            annotation=cst.Annotation(
                annotation=cst.Subscript(
                    value=cst.Name("type"), slice=[cst.SubscriptElement(cst.Index(cst.Name("_ModelT")))]
                )
            ),
        )

        for nullable in (True, False):  # Order matters!
            # sets `self: FieldName[<set_type>, <get_type>]`
            self_param = next(param for param in model_overload.params.params if param.name.value == "self")
            model_overload_ = model_overload.with_deep_changes(
                old_node=self_param, annotation=_build_self_annotation(field_cls_name, "_ModelT", nullable)
            )

            # sets `null: Literal[True/False]` (with the default removed accordingly)
            null_param = next(param for param in model_overload_.params.kwonly_params if param.name.value == "null")
            model_overload_ = model_overload_.with_deep_changes(
                old_node=null_param,
                annotation=cst.Annotation(
                    annotation=cst.Subscript(
                        value=cst.Name("Literal"), slice=[cst.SubscriptElement(cst.Index(cst.Name(str(nullable))))]
                    )
                ),
                default=None if nullable else null_param.default,  # Remove default to have a correct overload match
                equal=cst.MaybeSentinel.DEFAULT if nullable else null_param.equal,
            )

            overloads.append(model_overload_)

        new_body = list(updated_node.body.body)
        init_index = new_body.index(init_node)
        new_body.pop(init_index)

        new_body[init_index:init_index] = overloads

        return updated_node.with_deep_changes(old_node=updated_node.body, body=new_body)


def _build_self_annotation(field_cls_name: str, model_name: str, nullable: bool) -> cst.Annotation:
    """Builds the `self` annotation of foreign fields.

    With `field_cls_name="ForeignKey"`, `model_name="MyModel"` and `nullable=True`, the following is produced:

    `ForeignKey[MyModel | int | None, MyModel | None]`
    """
    # TODO handle FK types, currently assumed to be `int`
    none_part = " | None" if nullable else ""
    return cst.Annotation(
        annotation=helpers.parse_template_expression(
            f"{field_cls_name}[{model_name} | int{none_part}, {model_name}{none_part}]"
        )
    )
