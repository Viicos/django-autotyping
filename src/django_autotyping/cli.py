from __future__ import annotations

from argparse import ArgumentParser, ArgumentTypeError, Namespace
from pathlib import Path

from .codemods import RulesT, rules
from .main import main


class ScriptNamespace(Namespace):
    path: Path
    """Path to the directory containing the Django application."""

    settings_module: str | None

    diff: bool

    disable: list[RulesT] | None

    type_checking_block: bool

    assume_class_getitem: bool


def _dir_path(path_str: str) -> Path:
    if not (path := Path(path_str)).is_dir():
        raise ArgumentTypeError(f"{path_str} must be an existing directory.")
    return path


def parse_args() -> ScriptNamespace:
    parser = ArgumentParser(
        "django-autotyping",
        "Add type hints to your models for better auto-completion.",
    )

    parser.add_argument(
        "path",
        type=_dir_path,
        help="Path to the directory containing the Django application. "
        "This directory should contain your `manage.py` file.",
    )
    parser.add_argument(
        "--settings-module",
        default=None,
        help="Value of the `DJANGO_SETTINGS_MODULE` environment variable (a dotted Python path).",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show diff instead of applying changes to existing files.",
    )
    parser.add_argument(
        "--disable",
        choices=[rule[0] for rule in rules],
        nargs="*",
        help="Rules to be disabled.",
    )
    parser.add_argument(
        "--type-checking-block",
        action="store_true",
        help="Whether newly added imports should be in an `if TYPE_CHECKING` block (avoids circular imports).",
    )
    parser.add_argument(
        "--assume-class-getitem",
        action="store_true",
        help="Whether generic classes in stubs files but not at runtime should be assumed "
        "to have a `__class_getitem__` method. This can be achieved by using `django-stubs-ext` or manually.",
    )

    return parser.parse_args(namespace=ScriptNamespace())


def entrypoint() -> None:
    args = parse_args()

    main(args.path, args.settings_module, args.diff, args.disable, args.type_checking_block, args.assume_class_getitem)
