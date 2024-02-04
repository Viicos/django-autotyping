from __future__ import annotations

import libcst as cst
import libcst.matchers as m
from libcst import helpers
from libcst.codemod import CodemodContext

from django_autotyping.typing import FlattenFunctionDef

from ._utils import TypedDictAttribute, build_typed_dict, get_param, to_pascal
from .base import InsertAfterImportsVisitor, StubVisitorBasedCodemod
from .constants import OVERLOAD_DECORATOR

# Matchers:

CALL_COMMAND_DEF_MATCHER = m.FunctionDef(name=m.Name("call_command"))
"""Matches the `call_command` function definition."""


class CallCommandCodemod(StubVisitorBasedCodemod):
    """A codemod that will add overloads for [`call_command`][django.core.management.call_command].

    Rule identifier: `DJAS017`.

    ```python
    from django.core.management import call_command

    call_command("non_existing_cmd")  # Type error
    call_command("cmd", non_existing_arg="foo")  # Type error
    ```

    !!! info "Limited support"
        TBD
        https://github.com/microsoft/pylance-release/discussions/4148
    """

    STUB_FILES = {"core/management/__init__.pyi"}

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.add_typing_imports(["Literal", "Required", "TextIO", "TypedDict", "Unpack", "overload"])

    @m.leave(CALL_COMMAND_DEF_MATCHER)
    def mutate_CallCommandFunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> FlattenFunctionDef:
        overload = updated_node.with_changes(decorators=[OVERLOAD_DECORATOR])
        overloads: list[cst.FunctionDef] = []

        for command_name, command_info in self.django_context.management_commands_info.items():
            arg_info_list, options_info = command_info.actions_list[0]
            overload_ = overload.with_deep_changes(
                old_node=get_param(overload, "command_name"),
                annotation=cst.Annotation(helpers.parse_template_expression(f'Literal["{command_name}"]')),
            )
            if not arg_info_list:
                # No positional arguments, signature will be:
                # `call_command("cmd", **kwargs: Unpack[...])`
                overload_ = overload_.with_deep_changes(
                    old_node=overload_.params,
                    star_arg=cst.MaybeSentinel.DEFAULT,
                )

            # Build the kwargs annotation, with an unpacked TypedDict
            typed_dict_name = to_pascal(f"{command_name}") + "Options"
            options_typed_dict = build_typed_dict(
                name=typed_dict_name,
                attributes=[
                    TypedDictAttribute(
                        name=option_name,
                        annotation=option_info.type,
                        docstring=option_info.help,
                        required=option_info.required,
                    )
                    for option_name, option_info in options_info.items()
                ],
                leading_line=True,
                total=False,
            )
            InsertAfterImportsVisitor.insert_after_imports(self.context, [options_typed_dict])

            overload_ = overload_.with_deep_changes(
                old_node=overload_.params.star_kwarg,
                annotation=cst.Annotation(helpers.parse_template_expression(f"Unpack[{typed_dict_name}]")),
            )

            overloads.append(overload_)

        fallback_overload = overload.with_deep_changes(
            old_node=get_param(overload, "command_name"), annotation=cst.Annotation(cst.Name("BaseCommand"))
        )

        return cst.FlattenSentinel([*overloads, fallback_overload])

    def _mutate_CallCommandFunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> FlattenFunctionDef:
        overload = updated_node.with_changes(decorators=[OVERLOAD_DECORATOR])
        overloads: list[cst.FunctionDef] = []

        for command_name, command_info in self.django_context.management_commands_info.items():
            for i, (arg_info_list, options_info) in enumerate(command_info.actions_list, start=1):
                overload_ = overload.with_deep_changes(
                    old_node=get_param(overload, "command_name"),
                    annotation=cst.Annotation(helpers.parse_template_expression(f'Literal["{command_name}"]')),
                )

                if not arg_info_list:
                    # No positional arguments, signature will be:
                    # `call_command("cmd", **kwargs: Unpack[...])`
                    overload_ = overload_.with_deep_changes(
                        old_node=overload_.params,
                        star_arg=cst.MaybeSentinel.DEFAULT,
                    )
                elif command_info.use_star_args(arg_info_list):
                    args_annotation = f"*tuple[{', '.join(a.type for a in arg_info_list)}]"
                    overload_ = overload_.with_deep_changes(
                        old_node=overload_.params.star_arg,
                        annotation=cst.Annotation(helpers.parse_template_expression(args_annotation)),
                    )
                else:
                    # Fixed number of positional arguments, signature will be:
                    # `call_command("cmd", arg1: str, arg2: str, /, **kwargs: Unpack[...])`
                    parameters = overload_.params

                    # We move `command_name` to be pos only
                    posonly_params = [get_param(overload_, "command_name")]

                    for arg_info in arg_info_list:
                        if arg_info.nargs in (1, None):
                            posonly_params.append(
                                cst.Param(
                                    name=cst.Name(
                                        arg_info.dest or "tbd"
                                    ),  # "or" fallback if this is a subparser without `dest`
                                    # `arg_info.type` can safely be used here
                                    annotation=cst.Annotation(helpers.parse_template_expression(arg_info.type)),
                                )
                            )
                        else:
                            # only possible case is `nargs>=2`
                            for i in range(arg_info.nargs):
                                posonly_params.append(
                                    cst.Param(
                                        name=cst.Name(f"{arg_info.dest}_{i}"),
                                        annotation=cst.Annotation(cst.Name("str")),
                                    )
                                )

                    parameters = parameters.with_changes(
                        star_arg=cst.MaybeSentinel.DEFAULT,
                        params=[],
                        posonly_params=posonly_params,
                    )

                    overload_ = overload_.with_changes(
                        params=parameters,
                    )

                # Build the kwargs annotation, with an unpacked TypedDict
                typed_dict_name = to_pascal(f"{command_name}_options{i if len(command_info.actions_list) >= 2 else ''}")  # noqa: PLR2004
                options_typed_dict = build_typed_dict(
                    name=typed_dict_name,
                    attributes=[
                        TypedDictAttribute(
                            name=option_name,
                            annotation=option_info.type,
                            docstring=option_info.help,
                            required=option_info.required,
                        )
                        for option_name, option_info in options_info.items()
                    ],
                    leading_line=True,
                    total=False,
                )
                InsertAfterImportsVisitor.insert_after_imports(self.context, [options_typed_dict])

                overload_ = overload_.with_deep_changes(
                    old_node=overload_.params.star_kwarg,
                    annotation=cst.Annotation(helpers.parse_template_expression(f"Unpack[{typed_dict_name}]")),
                )

                overloads.append(overload_)

        fallback_overload = overload.with_deep_changes(
            old_node=get_param(overload, "command_name"), annotation=cst.Annotation(cst.Name("BaseCommand"))
        )

        return cst.FlattenSentinel([*overloads, fallback_overload])
