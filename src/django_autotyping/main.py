from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Collection

import libcst as cst
from django.conf import ENVIRONMENT_VARIABLE as DJANGO_SETTINGS_MODULE_ENV_KEY
from libcst.codemod import CodemodContext

from .codemods import ForwardRelationTypingVisitor, RulesT, gather_codemods
from .django_utils import parse_models, setup_django
from .vendoring.monkeytype import MoveImportsToTypeCheckingBlockVisitor, get_newly_imported_items


def main(
    app_path: os.PathLike[str],
    settings_module: str | None = None,
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
        code = Path(filename).read_text(encoding="utf-8")
        source_module = cst.parse_module(code)

        context = CodemodContext(
            filename=filename,
            scratch={},
        )
        filename_models = [model for model in model_infos if Path(model.filename) == Path(filename)]

        # TODO use gathered codemods
        visitor = ForwardRelationTypingVisitor(
            context=context,
            model_infos=filename_models,
        )

        output_module = visitor.transform_module(source_module)

        if type_checking_block:
            newly_imported_items = get_newly_imported_items(output_module, source_module)
            context = CodemodContext()
            MoveImportsToTypeCheckingBlockVisitor.store_imports_in_context(
                context,
                newly_imported_items,
            )
            type_checking_block_transformer = MoveImportsToTypeCheckingBlockVisitor(context)
            output_module = type_checking_block_transformer.transform_module(output_module)
        print(output_module.code)
