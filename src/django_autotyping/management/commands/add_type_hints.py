from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any, Iterable

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.utils.termcolors import colorize

from django_autotyping._compat import Unpack
from django_autotyping.app_settings import AutotypingSettings
from django_autotyping.codemodding.codemods import RulesT, gather_codemods, rules
from django_autotyping.codemodding.django_context import DjangoCodemodContext
from django_autotyping.codemodding.main import run_codemods

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
            "-p",
            "--project-dir",
            type=dir_path,
            help="The directory of the project, where code modifications should be applied.",
            required=at_settings.CODE_GENERATION.PROJECT_DIR is None,
            default=at_settings.CODE_GENERATION.PROJECT_DIR,
        )
        parser.add_argument(
            "--diff",
            action="store_true",
            help="Show changes to be applied instead of modifying existing files.",
            default=at_settings.CODE_GENERATION.DIFF,
        )
        parser.add_argument(
            "--ignore",
            choices=[rule[0] for rule in rules],
            nargs="*",
            help="Rules to be ignored.",
            default=at_settings.IGNORE,
        )

    def _colored_diff(self, lines: Iterable[str]) -> None:
        for line in lines:
            line_s = line.rstrip("\n")
            if line_s.startswith("+"):
                self.stdout.write(colorize(line_s, fg="green"))
            elif line_s.startswith("-"):
                self.stdout.write(colorize(line_s, fg="red"))
            elif line_s.startswith("^"):
                self.stdout.write(colorize(line_s, fg="blue"))
            else:
                self.stdout.write(line_s)

    def handle(self, *args: Any, **options: Unpack[CommandOptions]) -> None:
        django_context = DjangoCodemodContext(apps, settings, options["project_dir"])
        codemods = gather_codemods(options["ignore"])

        # TODO codemods should specify which type of file they apply to.
        model_filenames = set(model_info.filename for model_info in django_context.model_infos)

        for filename in model_filenames:
            intput_source = Path(filename).read_text("utf-8")
            output_source = run_codemods(codemods, django_context, at_settings.CODE_GENERATION, filename)
            if intput_source != output_source:
                if options["diff"]:
                    lines = difflib.unified_diff(
                        intput_source.splitlines(keepends=True),
                        output_source.splitlines(keepends=True),
                        fromfile=filename,
                        tofile=filename,
                    )
                    self._colored_diff(lines)
                else:
                    Path(filename).write_text(output_source, encoding="utf-8")
