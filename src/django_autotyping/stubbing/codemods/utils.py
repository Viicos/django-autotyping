from __future__ import annotations

from dataclasses import dataclass
from textwrap import indent

import libcst as cst
from libcst import helpers
from libcst import matchers as m


def get_method_node(class_node: cst.ClassDef, method_name: str) -> cst.FunctionDef:
    method_def = m.FunctionDef(name=m.Name(method_name))
    return helpers.ensure_type(
        next(node for node in class_node.body.body if m.matches(node, method_def)), cst.FunctionDef
    )


def get_param(node: cst.FunctionDef, param_name: str) -> cst.Param:
    """Get the `Param` node matching `param_name`."""
    return next(param for param in node.params.params if param.name.value == param_name)


def get_kw_param(node: cst.FunctionDef, param_name: str) -> cst.Param:
    """Get the keyword only `Param` node matching `param_name`."""
    return next(param for param in node.params.kwonly_params if param.name.value == param_name)


def _indent(string: str):
    return indent(string, prefix="    ", predicate=lambda line: not string.startswith(line))


@dataclass
class TypedDictField:
    name: str
    """The attribute name."""

    annotation: str
    """The annotation of the field."""

    docstring: str | None = None
    """The docstring of the field."""

    required: bool = False
    """Whether the field should be marked as `Required`."""

    not_required: bool = False
    """Whether the field should be marked as `NotRequired`."""

    def __post_init__(self):
        if self.required and self.not_required:
            raise ValueError("`required` and `not_required` can't be set together.")


def build_typed_dict(name: str, total: bool, fields: list[TypedDictField]) -> cst.ClassDef:
    body: list[cst.SimpleStatementLine] = []
    for field in fields:
        if field.required:
            annotation = f"Required[{field.annotation}]"
        elif field.not_required:
            annotation = f"NotRequired[{field.annotation}]"
        else:
            annotation = field.annotation

        body.append(helpers.parse_template_statement(annotation))

        if field.docstring:
            body.append(cst.SimpleStatementLine(body=[cst.Expr(cst.SimpleString(_indent(field.docstring)))]))

    return cst.ClassDef(
        name=cst.Name(name),
        keywords=[
            cst.Arg(
                keyword=cst.Name("total"),
                equal=cst.AssignEqual(cst.SimpleWhitespace(""), cst.SimpleWhitespace("")),
                value=cst.Name("False"),
            )
        ]
        if total
        else [],
        body=body,
    )
