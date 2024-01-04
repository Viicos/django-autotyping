import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    from typing import Unpack
else:
    from typing_extensions import Unpack  # noqa: F401


def is_relative_to(path: Path, other: Path) -> bool:
    if sys.version_info >= (3, 9):
        return path.is_relative_to(other)
    else:
        try:
            path.relative_to(other)
            return True
        except ValueError:
            return False
