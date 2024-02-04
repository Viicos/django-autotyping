from __future__ import annotations

import sys
from argparse import (
    ONE_OR_MORE,
    SUPPRESS,
    ZERO_OR_MORE,
    Action,
    _AppendAction,
    _AppendConstAction,
    _CountAction,
    _HelpAction,
    _StoreConstAction,
    _StoreFalseAction,
    _StoreTrueAction,
    _SubParsersAction,
    _VersionAction,
)
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Iterator, Literal, cast

from django.core.management import BaseCommand, get_commands, load_command_class
from django.core.management.base import CommandParser

from django_autotyping._compat import NoneType, Self, TypeGuard

BOOL_ACTIONS: tuple[type[Action], ...] = (
    _StoreTrueAction,
    _StoreFalseAction,
)

if sys.version_info >= (3, 9):
    from argparse import BooleanOptionalAction

    BOOL_ACTIONS += (BooleanOptionalAction,)

TYPE_MAP = {
    "str": str,
    "int": int,
    "float": float,
}


def get_commands_infos(commands: dict[str, str] | None = None) -> dict[str, CommandInfo]:
    """Returns a mapping of command names to a `CommandInfo` instance."""

    commands_infos: dict[str, CommandInfo] = {}
    commands = commands or get_commands()

    for command_name, app_name in commands.items():
        app_name = cast(BaseCommand | str, app_name)  # `django-stubs` is probably wrong
        if isinstance(app_name, BaseCommand):
            command = app_name
        else:
            try:
                command = load_command_class(app_name, command_name)
            except Exception:
                # Commands might fail on import
                continue
        parser = command.create_parser("", command_name)

        # 1. Deal with "stealth" actions. These will always be present in the signature(s).

        top_level_options_infos: dict[str, OptionInfo] = {}

        stealth_options = set(command.base_stealth_options + command.stealth_options)

        for option in stealth_options:
            option_info = OptionInfo(required=False)
            if option in {"stdout", "stderr"}:
                option_info.typing_imports.append("TextIO")
                option_info.type = "TextIO"

            # For the other stealth options, the default type (`Any`) is kept.
            top_level_options_infos[option] = option_info

        # 2. Build a list of two-tuples:
        # - The first element is a list of `ArgInfo` instances, will be used for the `*args` annotation
        # - The second element is a dict of `OptionInfo` instances, will be used for the `*kwargs` annotation
        # Most of the time, this list will only contain one tuple, which represents the actual signature
        # for this command. If subparsers are involved, the list will contain multiple elements and will map
        # to an overload.

        actions_list = list(
            _iter_actions(
                parser,
                is_subparser=False,
                parent_args=[],
                parent_options=top_level_options_infos,
            )
        )

        commands_infos[command_name] = CommandInfo(actions_list)

    return commands_infos


def _iter_actions(
    parser: CommandParser, is_subparser: bool, parent_args: list[ArgInfo], parent_options: dict[str, OptionInfo]
) -> Iterator[tuple[list[ArgInfo], dict[str, OptionInfo]]]:
    pos_actions = [action for action in parser._get_positional_actions() if not isinstance(action, _SubParsersAction)]

    arg_infos = parent_args + [ArgInfo(nargs=action.nargs, dest=action.dest) for action in pos_actions]
    options = {**parent_options, **get_options_infos(parser, is_subparser=is_subparser)}

    # TODO shouldn't yield if subparsers are required
    yield arg_infos, options

    subparsers_actions = [
        action for action in parser._get_positional_actions() if isinstance(action, _SubParsersAction)
    ]
    assert len(subparsers_actions) <= 1  # Only one `add_subparsers` call is allowed

    if subparsers_actions:
        subparser_action = subparsers_actions[0]
        for act in subparser_action._get_subactions():
            yield from _iter_actions(
                parser=subparser_action.choices[act.dest],
                is_subparser=True,
                parent_args=[
                    *arg_infos,
                    ArgInfo(
                        nargs=None,
                        dest=subparser_action.dest if subparser_action.dest != SUPPRESS else None,
                        subparser_arg=act.dest,
                    ),
                ],
                parent_options=options,
            )


def get_options_infos(parser: CommandParser, is_subparser: bool = False) -> dict[str, OptionInfo]:
    """Returns a mapping between the option names and `OptionInfo` instances.

    Depending on the action type, the type annotation will be adapted accordingly. For example,
    `append` actions will require the type annotation to be a list.

    If `is_subparser` is set, only the `dest` value will be used as an option name. This comes
    from the fact that the `call_command` somehow treats subparsers differently. For "top level"
    options, the option name (i.e. `--opt`) and `dest` will be available (if different).
    """

    # 1. `_AppendConstAction`/`_AppendAction` are handled separately. If more that two of them
    # points to the same dest, only `dest` is used as a possible argument, as it could otherwise
    # lead to some errors: if two actions `--foo` and `--bar` append to `dest` "baz", calling
    # "--foo 1 --bar 2" will result in "baz=['1', '2']".
    # However, `call_command(foo='1', bar='2')` will result in "baz='2'".
    # For subparsers, `call_command` only allows using `dest` anyway.

    options_dict: dict[str, OptionInfo] = {}

    append_actions_list = [
        action for action in parser._get_optional_actions() if isinstance(action, (_AppendConstAction, _AppendAction))
    ]

    append_const_actions: defaultdict[str, list[_AppendConstAction]] = defaultdict(list)
    append_actions: defaultdict[str, list[_AppendAction]] = defaultdict(list)

    for action in append_actions_list:
        if isinstance(action, _AppendConstAction):
            append_const_actions[action.dest].append(action)
        if isinstance(action, _AppendAction):
            append_actions[action.dest].append(action)

    for actions_dict in (append_const_actions, append_actions):
        for dest, action_list in actions_dict.items():
            if actions_dict is append_const_actions:
                option_info = OptionInfo.from_append_const_actions(*action_list)
            else:
                option_info = OptionInfo.from_append_actions(*action_list)

            if len(action_list) >= 2:  # noqa: PLR2004
                # We only accept the `dest` value as an argument to `call_command`
                # even if it is the parser is the main one.
                options_dict[dest] = option_info
            else:
                if not is_subparser:
                    action_name = min(action.option_strings).lstrip("-").replace("-", "_")
                    options_dict[action_name] = option_info

                if dest != action_name or is_subparser:
                    options_dict[dest] = deepcopy(option_info)

    # 2. Remaining actions

    remaining_actions = [
        action
        for action in parser._get_optional_actions()
        if not isinstance(action, (_HelpAction, _VersionAction, _AppendConstAction, _AppendAction))
    ]

    for action in remaining_actions:
        action_name = min(action.option_strings).lstrip("-").replace("-", "_")

        option_info = OptionInfo.from_action(action)

        if not is_subparser:
            options_dict[action_name] = option_info

        if action.dest != action_name or is_subparser:
            # Django allows both arguments, but only for top level options (for subparsers, only `dest`)
            options_dict[action.dest] = deepcopy(option_info)

    return options_dict


@dataclass
class CommandInfo:
    actions_list: list[tuple[list[ArgInfo], dict[str, OptionInfo]]]

    @staticmethod
    def use_star_args(arg_info_list: list[ArgInfo]) -> bool:
        """Whether `*args` should be used to annotate the positional arguments.

        This is the case for instance when an arbitrary number of arguments can be provided.
        """
        return any(arg_info.nargs in {"*", "+", "?"} for arg_info in arg_info_list)


@dataclass
class ArgInfo:
    nargs: Literal["*", "+", "?"] | int | None
    """The `nargs` argument of the action.

    A value of `None` has two meanings, depending on the value of `subparser_arg`.
    """

    dest: str | None = None
    """The `dest` argument of the action.

    Can take the value of `None` only if `suparser_arg` is set.
    """

    subparser_arg: str | None = None
    """If set, this `ArgInfo` instance represents a subparser action."""

    def __post_init__(self) -> None:
        if self.subparser_arg and self.nargs is not None:
            raise ValueError("A subparser argument cannot have nargs.")
        if not self.subparser_arg and self.dest is None:
            raise ValueError("dest cannot be None if this is not a subparser argument.")

    @property
    def type(self) -> str:
        """The type annotation to be used as part of the `*args` annotation.

        This is only relevant when building a more precise type for heterogeneous `*args`,
        as defined in PEP 646.

        Having a list of `ArgInfo` instances, the final annotation can be built this way:

        ```python
        arg_info_list: list[ArgInfo]
        args_annotation = f"*tuple[{', '.join(arg_info.star_args_type) for arg_info in arg_info_list}]"

        # Which would result in the following signature:
        def func(*args: *tuple[str, *tuple[str, ...], Literal["subcmd"]]): ...
        ```
        """
        if self.nargs is None:
            if self.subparser_arg:
                return f"Literal[{self.subparser_arg}]"
            return "str"
        if isinstance(self.nargs, int):
            return ", ".join("str" for _ in range(self.nargs))
        if self.nargs == "+":
            return "str, *tuple[str, ...]"
        if self.nargs in ["*", "?"]:  # TODO actual support for "?", ideally should generate overloads
            return "*tuple[str, ...]"


@dataclass
class OptionInfo:
    """A class holding information regarding a specific (optional) command option."""

    required: bool
    """Whether the option is required."""

    typing_imports: list[str] = field(default_factory=list)
    """A list of typing objects to be imported."""

    type: str = "Any"
    """The string representation of the option type."""

    help: str | None = None
    """The help text of the option."""

    @staticmethod
    def _get_type(action_type: Any) -> str:
        # TODO Support more types
        if action_type is None:
            return "str"
        if action_type in TYPE_MAP:
            return TYPE_MAP[action_type]
        return "Any"

    @classmethod
    def from_action(cls, action: Action) -> Self:
        typing_imports: list[str] = []

        if isinstance(action, _CountAction):
            type = "int"
        elif isinstance(action, BOOL_ACTIONS):
            # These actions do not have `nargs`/`type`
            # `BooleanOptionalAction` has a `type` arg but seems to be unused.
            type = "bool"
        elif isinstance(action, _StoreConstAction):
            # These actions do not have `nargs`/`type`
            # Type needs to be the type of `const`

            # First, try to represent it as a `Literal`:
            if _is_literal(action.const):
                typing_imports.append("Literal")
                type = f"Literal[{action.const!r}]"
            else:
                # Else, fallback to `Any` for now
                # TODO Support other `const` types, more work required as things should be imported
                typing_imports.append("Any")
                type = "Any"
        else:
            # TODO what to do with extend action?
            type = cls._get_type(action.type)
            if type == "Any":
                typing_imports.append("Any")

            if isinstance(action.nargs, int) or action.nargs in [ZERO_OR_MORE, ONE_OR_MORE]:
                type = f"list[{type}]"

        return cls(typing_imports=typing_imports, type=type, required=action.required, help=action.help)

    @classmethod
    def from_append_const_actions(cls, *actions: _AppendConstAction) -> Self:
        typing_imports: list[str] = []

        if all(_is_literal(action.const) for action in actions):
            typing_imports.append("Literal")
            type = f"list[Literal[{', '.join(repr(action.const) for action in actions)}]]"
        else:
            typing_imports.append("Any")
            type = "list[Any]"

        return cls(typing_imports=typing_imports, type=type, required=any(action.required for action in actions))

    @classmethod
    def from_append_actions(cls, *actions: _AppendAction) -> Self:
        typing_imports: list[str] = []

        types = [cls._get_type(action.type) for action in actions]
        if "Any" in types:
            typing_imports.append("Any")

        type = f"list[{' | '.join(types)}]"

        return cls(typing_imports=typing_imports, type=type, required=any(action.required for action in actions))


def _is_literal(const: Any) -> TypeGuard[str | bytes | int | bool | None]:
    # TODO Support for Enums
    return isinstance(const, (str, int, bool, NoneType)) or (isinstance(const, bytes) and const.isascii())
