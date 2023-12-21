from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor

if TYPE_CHECKING:
    from ..django_context import DjangoStubbingContext
    from ..stub_settings import StubSettings


TYPING_EXTENSIONS_NAMES = ["Unpack"]


class StubVisitorBasedCodemod(VisitorBasedCodemodCommand):
    """The base class for all codemods that apply to stub files."""

    STUB_FILES: ClassVar[set[str]]

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.django_context = cast("DjangoStubbingContext", context.scratch["django_context"])
        self.stub_settings = cast("StubSettings", context.scratch["stub_settings"])

    def add_model_imports(self) -> None:
        """Add the defined models in the Django context as imports to the current file."""

        # TODO LibCST should support adding imports from `ImportItem` objects
        imports = AddImportsVisitor._get_imports_from_context(self.context)
        imports.extend(self.django_context.model_imports)
        self.context.scratch[AddImportsVisitor.CONTEXT_KEY] = imports

    def add_typing_imports(self, names: list[str]) -> None:
        """Add imports to the `typing` module (either from `typing` or `typing_extensions`)"""
        for name in names:
            AddImportsVisitor.add_needed_import(
                self.context,
                module="typing_extensions" if name in TYPING_EXTENSIONS_NAMES else "typing",
                obj=name,
            )
