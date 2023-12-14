from pathlib import Path

from django.conf import settings

AUTOTYPING_STUBS_DIR: Path = getattr(settings, "AUTOTYPING_STUBS_DIR")
