from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from django_autotyping._compat import Unpack
from django_autotyping.app_settings import AutotypingSettings
from django_autotyping.codemodding.codemods import RulesT, rules

from ._utils import BaseOptions, dir_path

at_settings = AutotypingSettings(settings)


class CommandOptions(BaseOptions):
    project_dir: Path
    diff: bool
    ignore: list[RulesT] | None


class Command(BaseCommand):
    help = "Add type annotations to your Django code."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--project-dir",
            type=dir_path,
            help="The directory of the project, where code modifications should be applied.",
            default=at_settings.code_generation.project_path,
        )
        parser.add_argument(
            "--diff",
            action="store_true",
            help="Show changes to be applied instead of modifying existing files.",
            default=at_settings.code_generation.diff,
        )
        parser.add_argument(
            "--ignore",
            choices=[rule[0] for rule in rules],
            nargs="*",
            help="Rules to be ignored.",
            default=at_settings.ignore,
        )

    def handle(self, *args: Any, **options: Unpack[CommandOptions]) -> str | None:
        print(options)
