from __future__ import annotations

from pathlib import Path

import libcst as cst
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand

from django_autotyping.app_settings import CodeGenerationSettings

from .django_context import DjangoCodemodContext
from .vendoring.monkeytype import MoveImportsToTypeCheckingBlockVisitor, get_newly_imported_items


def run_codemods(
    codemods: list[type[VisitorBasedCodemodCommand]],
    django_context: DjangoCodemodContext,
    code_generation_settings: CodeGenerationSettings,
    filename: str,
) -> str:
    context = CodemodContext(
        filename=filename,
        scratch={
            "django_context": django_context,
            "code_generation_settings": code_generation_settings,
        },
    )

    input_code = Path(filename).read_text(encoding="utf-8")
    input_module = cst.parse_module(input_code)
    output_module = cst.parse_module(input_code)
    for codemod in codemods:
        transformer = codemod(context=context)

        output_module = transformer.transform_module(output_module)

    if code_generation_settings.TYPE_CHECKING_BLOCK:
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
