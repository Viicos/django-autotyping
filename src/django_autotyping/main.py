from __future__ import annotations

import difflib
import os
from pathlib import Path
from typing import Collection, Iterator

import libcst as cst
from django.conf import ENVIRONMENT_VARIABLE as DJANGO_SETTINGS_MODULE_ENV_KEY
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand

from .codemods import RulesT, gather_codemods
from .django_utils import DjangoContext
from .vendoring.monkeytype import MoveImportsToTypeCheckingBlockVisitor, get_newly_imported_items


def main(
    app_path: os.PathLike[str],
    settings_module: str | None = None,
    diff: bool = False,
    disabled_rules: Collection[RulesT] | None = None,
    type_checking_block: bool = True,
    assume_class_getitem: bool = False,
) -> None:
    settings_module = settings_module or os.getenv(DJANGO_SETTINGS_MODULE_ENV_KEY)
    if not settings_module:
        raise ValueError("No value was provided for --settings-module, and no environment variable was set.")

    disabled_rules = disabled_rules or []

    django_context = DjangoContext(settings_module, Path(app_path), assume_class_getitem)

    codemods = gather_codemods(disabled_rules)

    model_filenames = set(model_info.filename for model_info in django_context.model_infos)

    for filename in model_filenames:
        intput_source = Path(filename).read_text("utf-8")
        output_source = run_codemods(codemods, django_context, filename, type_checking_block)
        if intput_source != output_source:
            if diff:
                lines = difflib.unified_diff(
                    intput_source.splitlines(keepends=True),
                    output_source.splitlines(keepends=True),
                    fromfile=filename,
                    tofile=filename,
                )
                color_diff(lines)
            else:
                Path(filename).write_text(output_source, encoding="utf-8")


def run_codemods(
    codemods: list[type[VisitorBasedCodemodCommand]],
    django_context: DjangoContext,
    filename: str,
    type_checking_block: bool,
) -> str:
    context = CodemodContext(
        filename=filename,
        scratch={
            "django_context": django_context,
        },
    )

    input_code = Path(filename).read_text(encoding="utf-8")
    input_module = cst.parse_module(input_code)
    output_module = cst.parse_module(input_code)
    for codemod in codemods:
        transformer = codemod(context=context)

        output_module = transformer.transform_module(output_module)

    if type_checking_block:
        newly_imported_items = get_newly_imported_items(output_module, input_module)
        if newly_imported_items:
            context = CodemodContext()
            MoveImportsToTypeCheckingBlockVisitor.store_imports_in_context(
                context,
                newly_imported_items,
            )
            type_checking_block_transformer = MoveImportsToTypeCheckingBlockVisitor(context)
            output_module = type_checking_block_transformer.transform_module(output_module)

    return output_module.code


def color_diff(lines: Iterator[str]) -> None:
    for line in lines:
        line_s = line.rstrip("\n")
        if line_s.startswith("+"):
            print("\033[32m" + line_s + "\033[0m")
        elif line_s.startswith("-"):
            print("\033[31m" + line_s + "\033[0m")
        elif line_s.startswith("^"):
            print("\033[34m" + line_s + "\033[0m")
        else:
            print(line_s)
