from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Sequence, TypeVar, cast

import libcst as cst
import libcst.matchers as m
from libcst.codemod import CodemodContext, ContextAwareTransformer, VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor

if TYPE_CHECKING:
    from django_autotyping.app_settings import StubsGenerationSettings

    from ..django_context import DjangoStubbingContext


TYPING_EXTENSIONS_NAMES = ["Unpack", "Required", "NotRequired"]

ModuleT = TypeVar("ModuleT", bound=cst.Module)


IMPORT_MATCHER = m.SimpleStatementLine(body=[m.Import() | m.ImportFrom() | m.ImportAlias() | m.ImportStar()])
"""Matches the definition of an import statement."""


class InsertAfterImportsVisitor(ContextAwareTransformer):
    """Insert a list of statements after imports."""

    CONTEXT_KEY = "InsertAfterImportsVisitor"

    @classmethod
    def insert_after_imports(
        cls,
        context: CodemodContext,
        statements: Sequence[cst.SimpleStatementLine | cst.BaseCompoundStatement],
    ) -> None:
        """Insert a list of statements following the module imports.

        If no imports are to be found, statements will be added at the beginning of the module."""
        ctx_statements = context.scratch.get(cls.CONTEXT_KEY, [])
        ctx_statements.extend(statements)
        context.scratch[cls.CONTEXT_KEY] = ctx_statements

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        statements = self.context.scratch.get(self.CONTEXT_KEY, [])
        if not statements:
            return updated_node

        body = list(updated_node.body)

        last_import = next((node for node in reversed(body) if m.matches(node, IMPORT_MATCHER)), None)
        index = body.index(last_import) + 1 if last_import is not None else 0
        body[index:index] = statements

        return updated_node.with_changes(
            body=body,
        )


class StubVisitorBasedCodemod(VisitorBasedCodemodCommand):
    """The base class for all codemods used for custom stub files."""

    STUB_FILES: ClassVar[set[str]]

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.django_context = cast("DjangoStubbingContext", context.scratch["django_context"])
        self.stubs_settings = cast("StubsGenerationSettings", context.scratch["stubs_settings"])

    def add_model_imports(self) -> None:
        """Add the defined models in the Django context as imports to the current file."""

        # TODO LibCST should support adding imports from `ImportItem` objects
        imports = AddImportsVisitor._get_imports_from_context(self.context)
        imports.extend(self.django_context.model_imports)
        self.context.scratch[AddImportsVisitor.CONTEXT_KEY] = imports

    def add_typing_imports(self, names: list[str]) -> None:
        """Add imports to the `typing` module (either from `typing` or `typing_extensions`)."""
        for name in names:
            AddImportsVisitor.add_needed_import(
                self.context,
                module="typing_extensions" if name in TYPING_EXTENSIONS_NAMES else "typing",
                obj=name,
            )

    def transform_module(self, tree: cst.Module) -> cst.Module:
        # LibCST automatically runs `AddImportsVisitor` and `RemoveImportsVisitor`,
        # but this is hardcoded. So we manually add our visitor.
        tree = super().transform_module(tree)
        transform = InsertAfterImportsVisitor

        return self._instantiate_and_run(transform, tree)
