from __future__ import annotations

from pathlib import Path

from django.conf import settings

from .stubbing.codemods import RulesT

AUTOTYPING_STUBS_DIR: Path = Path(getattr(settings, "AUTOTYPING_STUBS_DIR"))
"""The directory pointing to local type stubs."""

AUTOTYPING_DISABLED_RULES: list[RulesT] = getattr(settings, "AUTOTYPING_DISABLED_RULES", [])
"""List of disabled stub rules."""
