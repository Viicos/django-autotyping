from __future__ import annotations

from typing import TYPE_CHECKING, cast

from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand

if TYPE_CHECKING:
    from django_autotyping.app_settings import CodeGenerationSettings

    from ..django_context import DjangoCodemodContext


class BaseVisitorBasedCodemod(VisitorBasedCodemodCommand):
    """The base class for all codemods used for Django user code."""

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.django_context = cast("DjangoCodemodContext", context.scratch["django_context"])
        self.code_generation_settings = cast("CodeGenerationSettings", context.scratch["code_generation_settings"])
