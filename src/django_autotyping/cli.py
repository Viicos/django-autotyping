from __future__ import annotations

import os
import sys
from argparse import ArgumentParser, ArgumentTypeError, Namespace
from pathlib import Path

from django.conf import ENVIRONMENT_VARIABLE as DJANGO_SETTINGS_MODULE_ENV_KEY

from .django_utils import parse_models, setup_django
from .main import main


class ScriptNamespace(Namespace):
    path: Path
    """Path to the directory containing the Django application."""

    settings_module: str | None


def _dir_path(path_str: str) -> Path:
    if not (path := Path(path_str)).is_dir():
        raise ArgumentTypeError(f"{path_str} must be an existing directory.")
    return path


def parse_args() -> ScriptNamespace:
    parser = ArgumentParser(
        "django-typing-helper",
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
        default=os.getenv(DJANGO_SETTINGS_MODULE_ENV_KEY),
        help="Value of the `DJANGO_SETTINGS_MODULE` environment variable (a dotted Python path).",
    )

    return parser.parse_args(namespace=ScriptNamespace())


def entrypoint() -> None:
    args = parse_args()

    if not args.settings_module:
        raise ValueError("No value was provided for --settings-module, and no environment variable was set.")
    os.environ[DJANGO_SETTINGS_MODULE_ENV_KEY] = args.settings_module

    # Patching `sys.path` to allow Django to setup correctly
    sys.path.append(str(args.path))
    setup_django()

    model_infos = parse_models(args.path)
    main(model_infos)
