from __future__ import annotations

import libcst as cst
import libcst.matchers as m
from libcst import helpers
from libcst.codemod import CodemodContext
from libcst.codemod.visitors import AddImportsVisitor
from libcst.metadata import ScopeProvider

from django_autotyping.typing import FlattenFunctionDef, ModelType

from .base import InsertAfterImportsVisitor, StubVisitorBasedCodemod
from .constants import OVERLOAD_DECORATOR
from .utils import get_kw_param, get_param

MODEL_T_TYPE_VAR = helpers.parse_template_statement('_ModelT = TypeVar("_ModelT", bound=Model)')
"""A statement assigning `_ModelT = TypeVar("_ModelT", bound=Model)`."""

# Matchers:

RELATED_CLASS_DEF_MATCHER = m.ClassDef(
    name=m.SaveMatchedNode(m.Name("ForeignObject") | m.Name("ForeignKey") | m.Name("OneToOneField"), "field_cls_name"),
)
"""Matches all foreign field class definitions that supports parametrization of the `__set__` and `__get__` types."""

MANY_TO_MANY_CLASS_DEF_MATCHER = m.ClassDef(name=m.Name("ManyToManyField"))
"""Matches the `ManyToManyField` class definition."""

INIT_DEF_MATCHER = m.FunctionDef(name=m.Name("__init__"))
"""Matches the `__init__` method definition."""


class ForwardRelationOverloadCodemod(StubVisitorBasedCodemod):
    """A codemod that will add overloads to the `__init__` methods of related fields.

    **Rule identifier**: `DJAS001`.

    **Related settings**:

    - [`ALLOW_PLAIN_MODEL_REFERENCES`][django_autotyping.app_settings.StubsGenerationSettings.ALLOW_PLAIN_MODEL_REFERENCES]
    - [`ALLOW_NONE_SET_TYPE`][django_autotyping.app_settings.StubsGenerationSettings.ALLOW_NONE_SET_TYPE]

    This will provide auto-completion when using [`ForeignKey`][django.db.models.ForeignKey],
    [`OneToOneField`][django.db.models.OneToOneField] and [`ManyToManyField`][django.db.models.ManyToManyField]
    with string references to a model, and accurate type checking when accessing the field attribute
    from a model instance.

    ```python
    class MyModel(models.Model):
        field = models.ForeignKey(
            "myapp.Other",
            on_delete=models.CASCADE,
        )
        nullable = models.OneToOneField(
            "myapp.Other",
            on_delete=models.CASCADE,
            null=True,
        )
    reveal_type(MyModel().field)  # Revealed type is "Other"
    reveal_type(MyModel().nullable)  # Revealed type is "Other | None"
    ```

    !!! info "Usage with VSCode"
        Auto-completion might not always work as expected, see this
        [issue](https://github.com/microsoft/pylance-release/issues/4428).


    ??? abstract "Implementation"
        The following is a snippet of the produced overloads:

        ```python
        class ForeignKey(ForeignObject[_ST, _GT]):
            # For each model, will add two overloads:
            # - 1st: `null: Literal[True]`, which will parametrize `ForeignKey` types as `Optional`.
            # - 2nd: `null: Literal[False] = ...` (the default).
            # `to` is annotated as a `Literal`, with two values: {app_label}.{model_name} and {model_name}.
            @overload
            def __init__(
                self: ForeignKey[MyModel | Combinable | None, MyModel | None],
                to: Literal["MyModel", "myapp.MyModel"],
                ...
            ) -> None: ...
        ```
    """  # noqa: E501

    METADATA_DEPENDENCIES = {ScopeProvider}
    STUB_FILES = {"db/models/fields/related.pyi"}

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.add_model_imports()
        InsertAfterImportsVisitor.insert_after_imports(context, [MODEL_T_TYPE_VAR])

        # Even though these are most likely included, we import them for safety:
        self.add_typing_imports(["Literal", "TypeVar", "overload"])

        AddImportsVisitor.add_needed_import(
            self.context,
            module="django.db.models.expressions",
            obj="Combinable",
        )

    @m.call_if_inside(MANY_TO_MANY_CLASS_DEF_MATCHER)
    @m.leave(INIT_DEF_MATCHER)
    def mutate_ManyToManyField_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> FlattenFunctionDef:
        """Add the necessary overloads for `ManyToManyField`'s `__init__` method.

        Due to combinatorial explosion, we can't add overloads that would handle `through` models alongside with `to`.
        """
        overload_init = updated_node.with_changes(decorators=[OVERLOAD_DECORATOR])
        overloads: list[cst.FunctionDef] = []

        for model in self.django_context.models:
            model_name = self.django_context.get_model_name(model)
            allow_plain_model_name = (
                self.stubs_settings.ALLOW_PLAIN_MODEL_REFERENCES and not self.django_context.is_duplicate(model)
            )

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
                annotation=_build_to_annotation(model, allow_plain_model_name),
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

        return cst.FlattenSentinel(overloads)

    @m.call_if_inside(RELATED_CLASS_DEF_MATCHER)
    @m.leave(INIT_DEF_MATCHER)
    def mutate_relatedFields_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> FlattenFunctionDef:
        """Add the necessary overloads to foreign fields that supports
        that supports parametrization of the `__set__` and `__get__` types.
        """
        field_cls_name = self.get_metadata(ScopeProvider, original_node).name

        overload_init = updated_node.with_changes(decorators=[OVERLOAD_DECORATOR])
        overloads: list[cst.FunctionDef] = []

        # For each model, create two overloads, depending on the `null` value:
        for model in self.django_context.models:
            model_name = self.django_context.get_model_name(model)
            allow_plain_model_name = (
                self.stubs_settings.ALLOW_PLAIN_MODEL_REFERENCES and not self.django_context.is_duplicate(model)
            )

            for nullable in (True, False):  # Order matters!
                # sets `self: FieldName[<set_type>, <get_type>]`
                self_param = get_param(overload_init, "self")
                overload = overload_init.with_deep_changes(
                    old_node=self_param,
                    annotation=_build_self_annotation(
                        field_cls_name, model_name, nullable, self.stubs_settings.ALLOW_NONE_SET_TYPE
                    ),
                )

                # sets `to: Literal["model_name", "app_label.model_name"]`
                to_param = get_param(overload, "to")
                overload = overload.with_deep_changes(
                    old_node=to_param,
                    annotation=_build_to_annotation(model, allow_plain_model_name),
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
                old_node=self_param,
                annotation=_build_self_annotation(
                    field_cls_name, "_ModelT", nullable, self.stubs_settings.ALLOW_NONE_SET_TYPE
                ),
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

        return cst.FlattenSentinel(overloads)


def _build_self_annotation(
    field_cls_name: str, model_name: str, nullable: bool, allow_none_set_type: bool
) -> cst.Annotation:
    """Builds the `self` annotation of foreign fields.

    With `field_cls_name="ForeignKey"`, `model_name="MyModel"` and `nullable=False`, the following is produced:

    >>> ForeignKey[MyModel | None, MyModel]

    (Even if not nullable, the `__set__` type can still be `None`. Having a foreign instance is only enforced on save).
    """
    set_type = f"{model_name} | Combinable | None" if allow_none_set_type or nullable else f"{model_name} | Combinable"
    get_type = f"{model_name} | None" if nullable else model_name
    return cst.Annotation(annotation=helpers.parse_template_expression(f"{field_cls_name}[{set_type}, {get_type}]"))


def _build_to_annotation(model: ModelType, allow_plain_model_name: bool) -> cst.Annotation:
    """Builds the `to` annotation of foreign fields.

    This will result in a `Literal` with two string values, the model name and the dotted app label and model name.
    If `allow_plain_model_name` is set to `False`, only the second literal value will be set.
    """
    slice = [cst.SubscriptElement(cst.Index(cst.SimpleString(f'"{model._meta.app_label}.{model.__name__}"')))]
    if allow_plain_model_name:
        slice.insert(0, cst.SubscriptElement(cst.Index(cst.SimpleString(f'"{model.__name__}"'))))

    return cst.Annotation(
        annotation=cst.Subscript(
            value=cst.Name("Literal"),
            slice=slice,
        )
    )
