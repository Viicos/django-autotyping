from __future__ import annotations

from pathlib import Path
from typing import Any

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from django_autotyping._compat import Unpack
from django_autotyping.app_settings import AutotypingSettings
from django_autotyping.stubbing import create_local_django_stubs, run_codemods
from django_autotyping.stubbing.codemods import RulesT, gather_codemods, rules
from django_autotyping.stubbing.django_context import DjangoStubbingContext

from ._utils import BaseOptions, dir_path

at_settings = AutotypingSettings.from_django_settings(settings)
stubs_settings = at_settings.stubs_generation


class CommandOptions(BaseOptions):
    local_stubs_dir: Path
    diff: bool
    ignore: list[RulesT] | None


class Command(BaseCommand):
    help = "Generate customized type stubs for your Django application."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "-s",
            "--local-stubs-dir",
            type=dir_path,
            help="The directory of the local type stubs.",
            required=at_settings.stubs_generation.local_stubs_dir is None,
            default=at_settings.stubs_generation.local_stubs_dir,
        )
        parser.add_argument(
            "--ignore",
            choices=[rule[0] for rule in rules],
            nargs="*",
            help="Rules to be ignored.",
            default=at_settings.ignore,
        )

    def handle(self, *args: Any, **options: Unpack[CommandOptions]) -> None:
        create_local_django_stubs(options["local_stubs_dir"], stubs_settings.source_stubs_dir)
        codemods = gather_codemods(options["ignore"])

        django_context = DjangoStubbingContext(apps, settings)
        run_codemods(codemods, django_context, stubs_settings)
