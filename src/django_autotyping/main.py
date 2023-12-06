from __future__ import annotations

import difflib
import os
import sys
from pathlib import Path
from typing import Collection

import libcst as cst
from django.conf import ENVIRONMENT_VARIABLE as DJANGO_SETTINGS_MODULE_ENV_KEY
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand

from .codemods import ForwardRelationTypingVisitor, RulesT, gather_codemods
from .django_utils import parse_models, setup_django
from .vendoring.monkeytype import MoveImportsToTypeCheckingBlockVisitor, get_newly_imported_items
from .models import ModelInfo


def main(
    app_path: os.PathLike[str],
    settings_module: str | None = None,
    diff: bool = False,
    disabled_rules: Collection[RulesT] | None = None,
    type_checking_block: bool = True,
) -> None:
    settings_module = settings_module or os.getenv(DJANGO_SETTINGS_MODULE_ENV_KEY)
    disabled_rules = disabled_rules or []

    if not settings_module:
        raise ValueError("No value was provided for --settings-module, and no environment variable was set.")

    os.environ[DJANGO_SETTINGS_MODULE_ENV_KEY] = settings_module

    # Patching `sys.path` to allow Django to setup correctly
    sys.path.append(str(app_path))
    setup_django()

    codemods = gather_codemods(disabled_rules)
    model_infos = parse_models(Path(app_path))

    model_filenames = set(model_info.filename for model_info in model_infos)

    for filename in model_filenames:
        filename_model_infos = [model for model in model_infos if Path(model.filename) == Path(filename)]
        lines = run_codemods(codemods, filename_model_infos, filename, diff, type_checking_block)
        if lines:
            color_diff(lines)


def run_codemods(
    codemods: list[type[VisitorBasedCodemodCommand]],
    model_infos: list[ModelInfo],
    filename: str,
    diff: bool,
    type_checking_block: bool,
) -> list[str]:
    context = CodemodContext(
        filename=filename,
        scratch={},
    )

    file_path = Path(filename)
    with file_path.open("r+", encoding="utf-8") as fp:
        input_code = fp.read()
        fp.seek(0)

        input_module = cst.parse_module(input_code)
        output_module = cst.parse_module(input_code)
        for codemod in codemods:
            transformer = codemod(context=context, model_infos=model_infos)  # TODO pass model_infos in context instead?

            output_module = transformer.transform_module(output_module)

        if type_checking_block:
            newly_imported_items = get_newly_imported_items(output_module, input_module)
            print(newly_imported_items)
            if newly_imported_items:
                context = CodemodContext()
                MoveImportsToTypeCheckingBlockVisitor.store_imports_in_context(
                    context,
                    newly_imported_items,
                )
                type_checking_block_transformer = MoveImportsToTypeCheckingBlockVisitor(context)
                output_module = type_checking_block_transformer.transform_module(output_module)

        output_code = output_module.code

        if output_code != input_code:
            if diff:
                lines = difflib.unified_diff(
                    input_code.splitlines(keepends=True),
                    output_code.splitlines(keepends=True),
                    fromfile=filename,
                    tofile=filename,
                )
                return list(lines)
            else:
                fp.write(output_code)
                fp.truncate()


def color_diff(lines: list[str]) -> None:
    for line in lines:
        line = line.rstrip("\n")
        if line.startswith("+"):
            print("\033[92m" + line + "\033[0m")
        elif line.startswith("-"):
            print("\033[91m" + line + "\033[0m")
        elif line.startswith("^"):
            print(line + "\033[0m")
        else:
            print(line + "\033[0m")
