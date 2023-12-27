from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
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
from .utils import TypedDictAttribute, build_typed_dict, get_param

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

# Helpers:

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


@dataclass
class LookupAnnotations:
    annotation_map: dict[str, tuple[str, bool]]
    """A mapping between the named arguments of a path and the annotation."""

    @property
    def is_empty(self) -> bool:
        return not self.annotation_map

    @property
    def sha1(self):
        return hashlib.sha1(self._stringified().encode("utf-8")).hexdigest()[:6]

    def __hash__(self) -> int:
        return hash(self._stringified())

    def _stringified(self) -> str:
        return "".join(f"{k}={v}" for k, v in self.annotation_map.items())

    @classmethod
    def from_argument_types(cls, arguments: dict[str, tuple[Any, bool]]) -> LookupAnnotations:
        # TODO custom converters: give instructions for users to set the annotation on their class
        return cls(annotation_map={k: (TYPE_MAP.get(type(v[0]), "Any"), v[1]) for k, v in arguments.items()})


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

        ann_viewnames_map: defaultdict[LookupAnnotations, list[str]] = defaultdict(list)

        for viewname, arguments in self.django_context.reverse_lookups.items():
            lookup_annotations = LookupAnnotations.from_argument_types(arguments)
            ann_viewnames_map[lookup_annotations].append(viewname)

        for lookup_annotations, viewnames in ann_viewnames_map.items():
            # We do not support `current_app` for now
            overload_ = overload.with_deep_changes(
                old_node=get_param(overload, "current_app"),
                annotation=cst.Annotation(LITERAL_NONE),
            )

            viewnames_literals = ", ".join(f'"{viewname}"' for viewname in viewnames)
            overload_ = overload_.with_deep_changes(
                old_node=get_param(overload_, "viewname"),
                annotation=cst.Annotation(helpers.parse_template_expression(f"Literal[{viewnames_literals}]")),
            )

            if lookup_annotations.is_empty:
                # Calling `reverse` with `args` or `kwargs` will fail at runtime
                # if the view has no arguments. We create a special overload handling this case:
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
                    args_str = ", ".join(el[0] for el in lookup_annotations.annotation_map.values())
                    annotation = helpers.parse_template_expression(f"tuple[{args_str}]")
                else:
                    annotation = LITERAL_NONE

                args_param = args_param.with_changes(
                    annotation=cst.Annotation(annotation),
                    default=None if use_args else args_param.default,
                    equal=cst.MaybeSentinel.DEFAULT if use_args else args_param.equal,
                )

                kwargs_param = get_param(overload, "kwargs")
                if use_args:
                    annotation = LITERAL_NONE
                else:
                    typed_dict_name = f"_{lookup_annotations.sha1.upper()}Kwargs"
                    typed_dict = build_typed_dict(
                        typed_dict_name,
                        attributes=[
                            TypedDictAttribute(
                                name=arg_name,
                                annotation=type_hint,
                                not_required=True if not required else None,
                                # TODO, any docstring?
                            )
                            for arg_name, (type_hint, required) in lookup_annotations.annotation_map.items()
                        ],
                        leading_line=True,
                    )

                    InsertAfterImportsVisitor.insert_after_imports(self.context, [typed_dict])

                    annotation = helpers.parse_template_expression(typed_dict_name)

                kwargs_param = kwargs_param.with_changes(
                    annotation=cst.Annotation(annotation),
                    default=None if not use_args else kwargs_param.default,
                    equal=cst.MaybeSentinel.DEFAULT if not use_args else kwargs_param.equal,
                )

                # Finally, add a `ParamStar` after `urlconf`, to have valid signatures.
                # Also move the necessary arguments as kwonly_params:

                overload__ = overload_.with_deep_changes(
                    old_node=overload_.params,
                    star_arg=cst.ParamStar(),
                    params=[p for p in overload_.params.params if p.name.value in ("viewname", "urlconf")],
                    kwonly_params=[args_param, kwargs_param, get_param(overload_, "current_app")],
                )

                overloads.append(overload__)

        # Remove the `str` annotation from `viewname` in the fallback overloads, so that
        # only literals will match:
        overload = overload.with_deep_changes(
            old_node=get_param(overload, "viewname"),
            annotation=cst.Annotation(helpers.parse_template_expression("Callable[..., Any] | None")),
        )

        return cst.FlattenSentinel(overloads + [overload])
