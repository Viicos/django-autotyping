from __future__ import annotations

from pathlib import Path
from typing import Any

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from django_autotyping._compat import Unpack
from django_autotyping.app_settings import AutotypingSettings
from django_autotyping.stubbing import create_local_django_stubs, run_codemods
from django_autotyping.stubbing.codemods import RulesT, gather_codemods, rules
from django_autotyping.stubbing.django_context import DjangoStubbingContext

from ._utils import BaseOptions, dir_path

at_settings = AutotypingSettings.from_django_settings(settings)
stubs_settings = at_settings.STUBS_GENERATION


class CommandOptions(BaseOptions):
    local_stubs_dir: Path
    ignore: list[RulesT] | None


class Command(BaseCommand):
    help = "Generate customized type stubs for your Django application."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "-s",
            "--local-stubs-dir",
            type=dir_path,
            help="The directory of the local type stubs.",
            required=at_settings.STUBS_GENERATION.LOCAL_STUBS_DIR is None,
            default=at_settings.STUBS_GENERATION.LOCAL_STUBS_DIR,
        )
        parser.add_argument(
            "--ignore",
            choices=[rule[0] for rule in rules],
            nargs="*",
            help="Rules to be ignored.",
            default=at_settings.IGNORE,
        )

    def handle(self, *args: Any, **options: Unpack[CommandOptions]) -> None:
        if not (stubs_dir := options["local_stubs_dir"]).is_dir():
            raise CommandError(f"The local stubs directory {stubs_dir} does not exist or is not a directory")

        if not (stubs_dir / "django-stubs").is_dir():
            self.stdout.write("Copying the 'django-stubs' package from site packages to the local stubs directory")
            create_local_django_stubs(options["local_stubs_dir"], stubs_settings.SOURCE_STUBS_DIR)
        codemods = gather_codemods(options["ignore"])

        django_context = DjangoStubbingContext(apps, settings)
        run_codemods(codemods, django_context, stubs_settings)
