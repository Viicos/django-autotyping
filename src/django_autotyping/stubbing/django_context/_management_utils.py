from __future__ import annotations

import sys
from argparse import (
    ONE_OR_MORE,
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
from typing import Any, Iterator, cast

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


def get_actions(parser: CommandParser) -> Iterator[Action]:
    # Parser actions and actions from sub-parser choices.
    for opt in parser._actions:
        if isinstance(opt, _SubParsersAction):
            yield opt
            for sub_opt in opt.choices.values():
                yield from get_actions(sub_opt)
        else:
            yield opt


def get_commands_info(commands: dict[str, str] | None = None):
    # Code is inspired from the actual `call_command` function implementation
    commands = commands or get_commands()
    for command_name, app_name in commands.items():
        app_name = cast(BaseCommand | str, app_name)  # `django-stubs` is probably wrong
        if isinstance(app_name, BaseCommand):
            command = app_name
        else:
            command = load_command_class(app_name, command_name)

        parser = command.create_parser("", command_name)

        # 1. Deal with "top level" actions. These will always be present in the signature(s),
        # even if subparsers are involved.

        top_level_options: dict[str, OptionInfo] = {}

        # 1.1. Stealth options

        stealth_options = set(command.base_stealth_options + command.stealth_options)

        for option in stealth_options:
            option_info = OptionInfo()
            if option in {"stdout", "stderr"}:
                option_info.typing_imports.append("TextIO")
                option_info.type = "TextIO"
            # For the other stealth options, the default type (`Any`) is kept.

            top_level_options[option] = option_info

        # 1.2. `_AppendConstAction`/`_AppendAction` are handled separately. If more that two of them
        # points to the same dest, only `dest` is used as a possible argument, as it could otherwise
        # lead to some errors: if two actions `--foo` and `--bar` append to dest `baz`, calling
        # "--foo 1 --bar 2" will result in "baz=['1', '2']".
        # However, `call_command(foo='1', bar='2')` will result in "baz='2'".

        append_actions_list = [
            action
            for action in parser._get_optional_actions()
            if isinstance(action, (_AppendConstAction, _AppendAction))
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
                    top_level_options[dest] = option_info
                else:
                    action_name = min(action.option_strings).lstrip("-").replace("-", "_")
                    top_level_options[action_name] = option_info

                    if dest != action_name:
                        top_level_options[dest] = deepcopy(option_info)

        # 1.3. Remaining actions

        top_level_optional_actions = [
            action
            for action in parser._get_optional_actions()
            if not isinstance(action, (_HelpAction, _VersionAction, _AppendConstAction, _AppendAction))
        ]

        for action in top_level_optional_actions:
            action_name = min(action.option_strings).lstrip("-").replace("-", "_")

            option_info = OptionInfo.from_action(action)

            top_level_options[action_name] = option_info

            if action.dest != action_name:
                # Django allows both arguments, but only for top level options (not subparsers)
                top_level_options[action.dest] = deepcopy(option_info)


@dataclass
class OptionInfo:
    required: bool
    typing_imports: list[str] = field(default_factory=list)
    type: str = "Any"

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

        return cls(typing_imports=typing_imports, type=type, required=action.required)

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

        return cls(typin_imports=typing_imports, type=type, required=any(action.required for action in actions))


def _is_literal(const: Any) -> TypeGuard[str | bytes | int | bool | None]:
    # TODO Support for Enums
    return isinstance(const, (str, int, bool, NoneType)) or (isinstance(const, bytes) and const.isascii())
