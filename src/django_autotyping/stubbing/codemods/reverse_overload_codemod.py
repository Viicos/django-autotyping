from __future__ import annotations

import re
from typing import Any

import libcst as cst
import libcst.matchers as m
from django.urls.converters import (
    IntConverter,
    PathConverter,
    SlugConverter,
    StringConverter,
    UUIDConverter,
)
from libcst import helpers
from libcst.codemod import CodemodContext
from libcst.codemod.visitors import AddImportsVisitor

from django_autotyping.typing import FlattenFunctionDef

from .base import InsertAfterImportsVisitor, StubVisitorBasedCodemod
from .constants import OVERLOAD_DECORATOR
from .utils import TypedDictAttribute, build_typed_dict, get_param, to_pascal

SUPPORTS_STR_DEF = helpers.parse_template_statement(
    """
class SupportsStr(Protocol):
    def __str__(self) -> str:
        ...
"""
)

EMPTY_DICT_DEF = helpers.parse_template_statement(
    """
class EmptyDict(TypedDict):
    pass
"""
)

LITERAL_NONE = helpers.parse_template_expression("Literal[None]")

# Matchers:

REVERSE_DEF_MATCHER = m.FunctionDef(name=m.Name("reverse"))
"""Matches the `reverse` function definition."""


class ReverseOverloadCodemod(StubVisitorBasedCodemod):
    """A codemod that will add overloads to the `reverse` function.

    Rule identifier: `DJAS011`.
    """

    STUB_FILES = {"urls/base.pyi"}

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)

        AddImportsVisitor.add_needed_import(
            context,
            module="uuid",
            obj="UUID",
        )
        InsertAfterImportsVisitor.insert_after_imports(context, [EMPTY_DICT_DEF, SUPPORTS_STR_DEF])
        self.add_typing_imports(["Literal", "TypedDict", "Protocol", "overload"])

    @m.leave(REVERSE_DEF_MATCHER)
    def mutate_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> FlattenFunctionDef:
        overload = updated_node.with_changes(decorators=[OVERLOAD_DECORATOR])
        overloads: list[cst.FunctionDef] = []

        for viewname, arguments in self.django_context.reverse_lookups.items():
            viewname_param = get_param(overload, "viewname")
            overloaded_viewname = overload.with_deep_changes(
                old_node=viewname_param,
                annotation=cst.Annotation(helpers.parse_template_expression(f'Literal["{viewname}"]')),
            )

            if not arguments:
                # Calling `reverse` with `args` or `kwargs` will fail at runtime
                # if the view has no arguments.
                overload_ = overloaded_viewname.with_deep_changes(
                    old_node=get_param(overloaded_viewname, "args"),
                    annotation=cst.Annotation(helpers.parse_template_expression("tuple[()]")),
                )
                overload_ = overload_.with_deep_changes(
                    old_node=get_param(overload_, "kwargs"),
                    annotation=cst.Annotation(helpers.parse_template_expression("EmptyDict")),
                )
                overloads.append(overload_)
                continue

            # If arguments are required, we add two overloads:

            argument_types = get_argument_types(arguments)

            for use_args in (True, False):
                args_param = get_param(overloaded_viewname, "args")
                if use_args:
                    args_str = ", ".join(argument_types.values())
                    annotation = helpers.parse_template_expression(f"tuple[{args_str}]")
                else:
                    annotation = LITERAL_NONE

                args_param = args_param.with_changes(
                    annotation=cst.Annotation(annotation),
                    default=None if use_args else args_param.default,
                    equal=cst.MaybeSentinel.DEFAULT if use_args else args_param.equal,
                )

                kwargs_param = get_param(overloaded_viewname, "kwargs")
                if use_args:
                    annotation = LITERAL_NONE
                else:
                    typed_dict_name = f"{to_pascal(as_identifier(viewname))}Kwargs"
                    typed_dict = build_typed_dict(
                        typed_dict_name,
                        attributes=[
                            TypedDictAttribute(
                                name=arg_name,
                                annotation=type_hint,  # TODO required/notrequired?
                                # TODO, any docstring?
                            )
                            for arg_name, type_hint in argument_types.items()
                        ],
                        leading_line=True,
                    )

                    # TODO create a visitor to add statements after imports, similar to the imports visitor
                    InsertAfterImportsVisitor.insert_after_imports(self.context, [typed_dict])

                    annotation = helpers.parse_template_expression(typed_dict_name)

                kwargs_param = kwargs_param.with_changes(
                    annotation=cst.Annotation(annotation),
                    default=None if not use_args else kwargs_param.default,
                    equal=cst.MaybeSentinel.DEFAULT if not use_args else kwargs_param.equal,
                )

                # We do not support `current_app` for now
                overload_ = overloaded_viewname.with_deep_changes(
                    old_node=get_param(overloaded_viewname, "current_app"),
                    annotation=cst.Annotation(LITERAL_NONE),
                )

                # Finally, add a `ParamStar` after `urlconf`, to have valid signatures.
                # Also move the necessary arguments as kwonly_params:

                overload_ = overload_.with_deep_changes(
                    old_node=overload_.params,
                    star_arg=cst.ParamStar(),
                    params=[p for p in overload_.params.params if p.name.value in ("viewname", "urlconf")],
                    kwonly_params=[args_param, kwargs_param, get_param(overload_, "current_app")],
                )

                overloads.append(overload_)

        return cst.FlattenSentinel(overloads + [overload])


# `SupportsStr` is a Protocol that supports `__str__`.
# This should be equivalent to `object`, but is used to be
# more explicit (same applies to the first union type, it is here for explicitness).
TYPE_MAP = {
    IntConverter: "int | SupportsStr",
    StringConverter: "str | SupportsStr",
    UUIDConverter: "UUID | SupportsStr",
    SlugConverter: "str | SupportsStr",
    PathConverter: "str | SupportsStr",
}


def get_argument_types(arguments: dict[str, Any]):
    return {k: TYPE_MAP.get(type(v), "Any") for k, v in arguments.items()}


def as_identifier(string: str) -> str:
    return re.sub(r"\W|^(?=\d)", "_", string)
