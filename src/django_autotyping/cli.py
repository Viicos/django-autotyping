from __future__ import annotations

from argparse import ArgumentParser, ArgumentTypeError, Namespace
from pathlib import Path

from .codemods import RulesT, rules
from .main import main


class ScriptNamespace(Namespace):
    path: Path
    """Path to the directory containing the Django application."""

    settings_module: str | None

    disable: list[RulesT] | None

    type_checking_block: bool


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
        "--disable",
        choices=[rule[0] for rule in rules],
        nargs="*",
        help="Rules to be disabled.",
    )
    parser.add_argument(
        "--type-checking-block",
        action="store_true",
        default=False,
        help="Whether newly added imports should be in an `if TYPE_CHECKING` block (avoids circular imports).",
    )

    return parser.parse_args(namespace=ScriptNamespace())


def entrypoint() -> None:
    args = parse_args()

    main(args.path, args.settings_module, args.disable, args.type_checking_block)
