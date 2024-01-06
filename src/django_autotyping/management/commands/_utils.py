from __future__ import annotations

from argparse import ArgumentTypeError
from pathlib import Path
from typing import Literal, TypedDict


def dir_path(path_str: str) -> Path:
    if path_str and not (path := Path(path_str)).is_dir():
        raise ArgumentTypeError(f"{path_str} must be an existing directory.")
    return path


class BaseOptions(TypedDict):
    verbosity: Literal[0, 1, 2, 3]
    """Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, 3=very verbose output"""

    settings: str | None
    """The Python path to a settings module, e.g. "myproject.settings.main". If this isn't provided,
    the DJANGO_SETTINGS_MODULE environment variable will be used.
    """

    pythonpath: str | None
    """A directory to add to the Python path, e.g. "/home/djangoprojects/myproject"."""

    traceback: bool
    """Raise on CommandError exceptions."""

    no_color: bool
    """Don't colorize the command output."""

    skip_checks: bool
    """Skip system checks."""
