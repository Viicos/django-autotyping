from typing import cast

import libcst as cst
import libcst.matchers as m
from libcst import helpers
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor

from django_autotyping.typing import ModelType

from .utils import get_kw_param, get_method_node, get_model_alias, get_model_imports, get_param, is_duplicate_model

OVERLOAD_DECORATOR = cst.Decorator(decorator=cst.Name("overload"))

MODEL_T_TYPE_VAR = helpers.parse_template_statement('_ModelT = TypeVar("_ModelT", bound=Model)')
"""A statement assigning `_ModelT = TypeVar("_ModelT", bound=Model)`."""

# Matchers:

RELATED_CLASS_DEF_MATCHER = m.ClassDef(
    name=m.SaveMatchedNode(m.Name("ForeignObject") | m.Name("ForeignKey") | m.Name("OneToOneField"), "field_cls_name"),
)
"""Matches all foreign field class definitions that supports parametrization of the `__set__` and `__get__` types."""

MANY_TO_MANY_CLASS_DEF_MATCHER = m.ClassDef(name=m.Name("ManyToManyField"))
"""Matches the `ManyToManyField` class definition."""


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
        # - 1st: `null: Literal[True]`, which will parametrize `ForeignKey` get types as `Optional`.
        # - 2nd: `null: Literal[False] = ...` (the default).
        # `to` is annotated as a `Literal`, with two values: {app_label}.{model_name} and {model_name}.
        @overload
        def __init__(
            self: ForeignKey[MyModel | None, MyModel | None],
            to: Literal["MyModel", "myapp.MyModel"],
            ...
        ) -> None: ...
    ```
    """

    STUB_FILES = {"db/models/fields/related.pyi"}

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

    @m.leave(MANY_TO_MANY_CLASS_DEF_MATCHER)
    def mutate_ManyToManyField_classDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        """Add the necessary overloads for `ManyToManyField`.

        Due to combinatorial explosion, we can't add overloads that would handle `through` models alongside with `to`.
        """
        init_node = get_method_node(updated_node, "__init__")
        overload_init = init_node.with_changes(decorators=[OVERLOAD_DECORATOR])

        overloads: list[cst.FunctionDef] = []

        for model in self.django_models:
            # TODO This needs a proper Django Context object, instead of these utilities
            model_name = get_model_alias(model, self.django_models) or model.__name__
            duplicate = is_duplicate_model(model.__name__, self.django_models)

            # sets `self: ManyToManyField[model_name, _Through]`
            self_param = get_param(overload_init, "self")
            overload = overload_init.with_deep_changes(
                old_node=self_param,
                annotation=cst.Annotation(
                    annotation=helpers.parse_template_expression(f"ManyToManyField[{model_name}, _Through]")
                ),
            )

            # sets `to: Literal["model_name", "app_label.model_name"]`
            # (or just "app_label.model_name" if duplicate model names)
            to_param = get_param(overload, "to")
            overload = overload.with_deep_changes(
                old_node=to_param,
                annotation=_build_to_annotation(model, duplicate),
            )

            overloads.append(overload)

        # Now, handle the last overload, matching against a real model type:

        # sets `to: type[_To]`, essentially removing the `| str` part. This way,
        # we don't need to explicitly annotate `self`, type checkers will infer this natively.
        to_param = get_param(overload_init, "to")
        model_overload = overload_init.with_deep_changes(
            old_node=to_param,
            annotation=cst.Annotation(
                annotation=cst.Subscript(
                    value=cst.Name("type"), slice=[cst.SubscriptElement(cst.Index(cst.Name("_To")))]
                )
            ),
        )

        overloads.append(model_overload)

        new_body = list(updated_node.body.body)
        init_index = new_body.index(init_node)
        new_body.pop(init_index)

        new_body[init_index:init_index] = overloads

        return updated_node.with_deep_changes(old_node=updated_node.body, body=new_body)

    @m.leave(RELATED_CLASS_DEF_MATCHER)
    def mutate_classDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        """Add the necessary overloads to foreign fields that supports
        that supports parametrization of the `__set__` and `__get__` types.
        """
        extracted = m.extract(updated_node, RELATED_CLASS_DEF_MATCHER)
        field_cls_name: str = extracted.get("field_cls_name").value

        init_node = get_method_node(updated_node, "__init__")
        overload_init = init_node.with_changes(decorators=[OVERLOAD_DECORATOR])

        overloads: list[cst.FunctionDef] = []

        # For each model, create two overloads, depending on the `null` value:
        for model in self.django_models:
            # TODO This needs a proper Django Context object, instead of these utilities
            model_name = get_model_alias(model, self.django_models) or model.__name__
            duplicate = is_duplicate_model(model.__name__, self.django_models)

            for nullable in (True, False):  # Order matters!
                # sets `self: FieldName[<set_type>, <get_type>]`
                self_param = get_param(overload_init, "self")
                overload = overload_init.with_deep_changes(
                    old_node=self_param,
                    annotation=_build_self_annotation(field_cls_name, model_name, nullable),
                )

                # sets `to: Literal["model_name", "app_label.model_name"]`
                to_param = get_param(overload, "to")
                overload = overload.with_deep_changes(
                    old_node=to_param,
                    annotation=_build_to_annotation(model, duplicate),
                )

                # sets `null: Literal[True/False]` (with the default removed accordingly)
                null_param = get_kw_param(overload, "null")
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

        # sets `to: type[_ModelT]`, the type variable will be used to annotate `self` as well
        to_param = get_param(overload_init, "to")
        model_overload = overload_init.with_deep_changes(
            old_node=to_param,
            annotation=cst.Annotation(
                annotation=cst.Subscript(
                    value=cst.Name("type"), slice=[cst.SubscriptElement(cst.Index(cst.Name("_ModelT")))]
                )
            ),
        )

        for nullable in (True, False):  # Order matters!
            # sets `self: FieldName[<set_type>, <get_type>]`
            self_param = get_param(model_overload, "self")
            model_overload_ = model_overload.with_deep_changes(
                old_node=self_param, annotation=_build_self_annotation(field_cls_name, "_ModelT", nullable)
            )

            # sets `null: Literal[True/False]` (with the default removed accordingly)
            null_param = get_kw_param(model_overload_, "null")
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

        # Temp workaround to have autocompletion working, this overload shouldn't be used as a match by type checkers
        # to_param = get_param(overload_init, "to")
        # literal_completion_overload = overload_init.with_deep_changes(
        #     old_node=to_param,
        #     annotation=cst.Annotation(
        #         annotation=cst.Subscript(
        #             value=cst.Name("Literal"),
        #             slice=[
        #                 cst.SubscriptElement(cst.Index(cst.SimpleString(string)))
        #                 for model in self.django_models
        #                 for string in (f'"{model.__name__}"', f'"{model._meta.app_label}.{model.__name__}"')
        #             ],
        #         )
        #     ),
        # )

        # overloads.append(literal_completion_overload)

        new_body = list(updated_node.body.body)
        init_index = new_body.index(init_node)
        new_body.pop(init_index)

        new_body[init_index:init_index] = overloads

        return updated_node.with_deep_changes(old_node=updated_node.body, body=new_body)


def _build_self_annotation(field_cls_name: str, model_name: str, nullable: bool) -> cst.Annotation:
    """Builds the `self` annotation of foreign fields.

    With `field_cls_name="ForeignKey"`, `model_name="MyModel"` and `nullable=False`, the following is produced:

    >>> ForeignKey[MyModel | None, MyModel]

    (Even if not nullable, the `__set__` type can still be `None`. Having a foreign instance is only enforced on save).
    """
    none_part = " | None" if nullable else ""
    return cst.Annotation(
        annotation=helpers.parse_template_expression(f"{field_cls_name}[{model_name} | None, {model_name}{none_part}]")
    )


def _build_to_annotation(model: ModelType, duplicate: bool = False) -> cst.Annotation:
    """Builds the `to` annotation of foreign fields.

    This will result in a `Literal` with two string values, the model name and the dotted app label and model name.
    If `duplicate` is set to `True`, only the second literal value will be set.
    """
    slice = [cst.SubscriptElement(cst.Index(cst.SimpleString(f'"{model._meta.app_label}.{model.__name__}"')))]
    if not duplicate:
        slice.insert(0, cst.SubscriptElement(cst.Index(cst.SimpleString(f'"{model.__name__}"'))))

    return cst.Annotation(
        annotation=cst.Subscript(
            value=cst.Name("Literal"),
            slice=slice,
        )
    )
