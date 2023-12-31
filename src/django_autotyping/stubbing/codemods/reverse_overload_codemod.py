from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

import libcst as cst
import libcst.matchers as m
from libcst import helpers
from libcst.codemod import CodemodContext
from libcst.codemod.visitors import AddImportsVisitor

from django_autotyping.typing import FlattenFunctionDef

from .base import InsertAfterImportsVisitor, StubVisitorBasedCodemod
from .constants import OVERLOAD_DECORATOR
from .utils import TypedDictAttribute, build_typed_dict, get_param

if TYPE_CHECKING:
    from ..django_context import PathInfo

# `SupportsStr` is a Protocol that supports `__str__`.
# This should be equivalent to `object`, but is used to be
# more explicit.
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
        self.add_typing_imports(["Literal", "TypedDict", "NotRequired", "Protocol", "overload"])

    @m.leave(REVERSE_DEF_MATCHER)
    def mutate_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> FlattenFunctionDef:
        overload = updated_node.with_changes(decorators=[OVERLOAD_DECORATOR])

        overloads: list[cst.FunctionDef] = []
        seen_kwargs_hashes: list[str] = []
        reversed_dict: defaultdict[PathInfo, list[str]] = defaultdict(list)

        # First, build a reverse dictionary: a mapping between PathInfos instances (shared between views)
        # and a list of viewnames

        for viewname, path_info in self.django_context.viewnames_lookups.items():
            reversed_dict[path_info].append(viewname)

        for path_info, viewnames in reversed_dict.items():
            # We do not support `current_app` for now, it would generate too many overloads
            overload_ = overload.with_deep_changes(
                old_node=get_param(overload, "current_app"),
                annotation=cst.Annotation(LITERAL_NONE),
            )

            viewnames_literals = ", ".join(f'"{viewname}"' for viewname in viewnames)
            overload_ = overload_.with_deep_changes(
                old_node=get_param(overload_, "viewname"),
                annotation=cst.Annotation(helpers.parse_template_expression(f"Literal[{viewnames_literals}]")),
            )

            if path_info.is_empty:
                # Calling `reverse` with `args` or `kwargs` will fail at runtime if the view has no arguments.
                # We create a special overload handling this case:
                overload_ = overload_.with_deep_changes(
                    old_node=get_param(overload_, "args"),
                    annotation=cst.Annotation(helpers.parse_template_expression("tuple[()] | None")),
                )
                overload_ = overload_.with_deep_changes(
                    old_node=get_param(overload_, "kwargs"),
                    annotation=cst.Annotation(helpers.parse_template_expression("EmptyDict | None")),
                )
                overloads.insert(0, overload_)
                continue

            for use_args in (True, False):
                args_param = get_param(overload_, "args")
                if use_args:
                    annotation = helpers.parse_template_expression(path_info.get_args_annotation())
                else:
                    annotation = LITERAL_NONE

                args_param = args_param.with_changes(
                    annotation=cst.Annotation(annotation),
                    default=None if use_args else args_param.default,
                    equal=cst.MaybeSentinel.DEFAULT if use_args else args_param.equal,
                )

                kwargs_param = get_param(overload_, "kwargs")
                if use_args:
                    annotation = LITERAL_NONE
                else:
                    annotation = helpers.parse_template_expression(path_info.get_kwargs_annotation())
                    for kwargs in path_info.kwargs_list:
                        kwargs_hash = path_info.get_kwargs_hash(kwargs)
                        if kwargs_hash in seen_kwargs_hashes:
                            continue

                        seen_kwargs_hashes.append(kwargs_hash)
                        typed_dict_name = path_info.get_typeddict_name(kwargs)
                        typed_dict = build_typed_dict(
                            typed_dict_name,
                            attributes=[
                                TypedDictAttribute(
                                    name=arg_name,
                                    annotation="SupportsStr",
                                    not_required=True if not required else None,
                                    # TODO, any docstring?
                                )
                                for arg_name, required in kwargs.items()
                            ],
                            leading_line=True,
                        )

                        InsertAfterImportsVisitor.insert_after_imports(self.context, [typed_dict])

                kwargs_param = kwargs_param.with_changes(
                    annotation=cst.Annotation(annotation),
                    default=None if not use_args else kwargs_param.default,
                    equal=cst.MaybeSentinel.DEFAULT if not use_args else kwargs_param.equal,
                )

                # Finally, add a `ParamStar` after `urlconf`, to have valid signatures.
                # Also move the necessary arguments as kwonly_params:

                overload_param_star = overload_.with_deep_changes(
                    old_node=overload_.params,
                    star_arg=cst.ParamStar(),
                    params=[p for p in overload_.params.params if p.name.value in ("viewname", "urlconf")],
                    kwonly_params=[args_param, kwargs_param, get_param(overload_, "current_app")],
                )

                overloads.append(overload_param_star)

        # Remove the `str` annotation from `viewname` in the fallback overloads, so that
        # only literals will match:
        overload = overload.with_deep_changes(
            old_node=get_param(overload, "viewname"),
            annotation=cst.Annotation(helpers.parse_template_expression("Callable[..., Any] | None")),
        )

        return cst.FlattenSentinel(overloads + [overload])
