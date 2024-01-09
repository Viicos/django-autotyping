from __future__ import annotations

import re
from dataclasses import dataclass

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
    try:
        return next(param for param in node.params.params if param.name.value == param_name)
    except StopIteration:
        raise RuntimeError(
            f"The `FunctionDef` node with name {node.name.value!r} does not have any parameter named {param_name!r}"
        )


def get_kw_param(node: cst.FunctionDef, param_name: str) -> cst.Param:
    """Get the keyword only `Param` node matching `param_name`."""
    return next(param for param in node.params.kwonly_params if param.name.value == param_name)


def to_pascal(string) -> str:
    return re.sub("([0-9A-Za-z])_(?=[0-9A-Z])", lambda m: m.group(1), string.title())


def _indent(string: str) -> str:
    return string.replace("\n", "\n    ")


@dataclass
class TypedDictAttribute:
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

    @property
    def marked_annotation(self) -> str:
        """The annotation additionally marked as required or not required."""
        if self.required:
            return f"Required[{self.annotation}]"
        if self.not_required:
            return f"NotRequired[{self.annotation}]"
        return self.annotation

    def __post_init__(self):
        if self.required and self.not_required:
            raise ValueError("`required` and `not_required` can't be set together.")


def build_typed_dict(
    name: str, attributes: list[TypedDictAttribute], total: bool = True, leading_line: bool = False
) -> cst.SimpleStatementLine | cst.ClassDef:
    """Build a `TypedDict` class definition.

    If one of the attribute's name is not a valid Python identifier, the alternative functional syntax
    will be used (a `SimpleStatementLine` will be created instead of a `ClassDef`).

    Args:
        name: The name of the resulting class.
        attributes: A list of `TypedDictAttribute` instances, representing attributes of the dict.
        total: Whether `total=True` should be used.
        leadind_line: Whether an empty leading line should be added before the class definition.

    """
    functional = any(not attr.name.isidentifier() for attr in attributes)
    leading_lines = [cst.EmptyLine(indent=False)] if leading_line else []
    if not functional:
        body: list[cst.SimpleStatementLine] = []

        for attr in attributes:
            ann_statement = helpers.parse_template_statement(f"{attr.name}: {attr.marked_annotation}")
            if attributes.index(attr) != 0:
                ann_statement = ann_statement.with_changes(leading_lines=[cst.EmptyLine(indent=False)])
            body.append(ann_statement)

            if attr.docstring:
                docstring = f'"""{_indent(attr.docstring)}"""'
                body.append(cst.SimpleStatementLine(body=[cst.Expr(cst.SimpleString(docstring))]))

        return cst.ClassDef(
            name=cst.Name(name),
            bases=[cst.Arg(cst.Name("TypedDict"))],
            keywords=[
                cst.Arg(
                    keyword=cst.Name("total"),
                    equal=cst.AssignEqual(cst.SimpleWhitespace(""), cst.SimpleWhitespace("")),
                    value=cst.Name("False"),
                )
            ]
            if not total
            else [],
            body=cst.IndentedBlock(body),
            leading_lines=leading_lines,
        )

    # If some attributes aren't Python identifiers, we use the functional form:
    # name = TypedDict("name", {"x": int, "y": int})
    return cst.SimpleStatementLine(
        body=[
            cst.Assign(
                targets=[cst.AssignTarget(cst.Name(name))],
                value=cst.Call(
                    func=cst.Name("TypedDict"),
                    args=[
                        cst.Arg(cst.SimpleString(f'"{name}"')),
                        cst.Arg(
                            cst.Dict(
                                elements=[
                                    cst.DictElement(
                                        key=cst.SimpleString(f'"{attr.name}"'), value=cst.Name(attr.marked_annotation)
                                    )
                                    for attr in attributes
                                ]
                            )
                        ),
                    ],
                ),
            )
        ],
        leading_lines=leading_lines,
    )
