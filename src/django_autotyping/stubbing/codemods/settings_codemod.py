from __future__ import annotations

import inspect

import libcst as cst
import libcst.matchers as m
from libcst import helpers
from libcst.codemod.visitors import AddImportsVisitor

from django_autotyping._compat import NoneType

from ._global_settings_types import GLOBAL_SETTINGS, SettingTypingConfiguration
from ._utils import _indent
from .base import InsertAfterImportsVisitor, StubVisitorBasedCodemod

# Matchers:

CLASS_DEF_MATCHER = m.ClassDef(name=m.Name("LazySettings"))
"""Matches the `LazySettings` class definition."""


TYPE_MAP = {
    int: "int",
    str: "str",
    NoneType: "Literal[None]",
}


class SettingCodemod(StubVisitorBasedCodemod):
    """A codemod that will add typing to the Django settings object.

    Rule identifier: `DJAS016`.

    ```python
    from django.conf import settings

    reveal_type(settings.ADMINS)  # Revealed type is "list[tuple[str, str]]"
    ```
    """

    STUB_FILES = {"conf/__init__.pyi"}

    def _get_statement_lines(
        self, setting_name: str, setting_typing_conf: SettingTypingConfiguration
    ) -> list[cst.SimpleStatementLine]:
        lines = [
            cst.SimpleStatementLine(
                [
                    cst.AnnAssign(
                        target=cst.Name(setting_name),
                        annotation=cst.Annotation(helpers.parse_template_expression(setting_typing_conf["type"])),
                    )
                ]
            ),
        ]
        if docstring := setting_typing_conf.get("docs"):
            docstring = f'"""{_indent(docstring.strip())}"""'
            lines.append(cst.SimpleStatementLine([cst.Expr(cst.SimpleString(docstring))]))
        return lines

    @m.leave(CLASS_DEF_MATCHER)
    def mutate_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        body = list(updated_node.body.body)
        # TODO special case AUTH_MODEL to be a literal, so that it plays well with foreign keys
        for setting in dir(self.django_context.settings._wrapped):
            if setting != "SETTINGS_MODULE" and setting.isupper():
                global_setting_conf = GLOBAL_SETTINGS.get(setting)
                if global_setting_conf is not None:
                    # This is a global setting, use the already defined type:

                    if typing_imports := global_setting_conf.get("typing_imports"):
                        self.add_typing_imports(typing_imports)
                    if extra_imports := global_setting_conf.get("extra_imports"):
                        imports = AddImportsVisitor._get_imports_from_context(self.context)
                        imports.extend(extra_imports)
                        self.context.scratch[AddImportsVisitor.CONTEXT_KEY] = imports
                    if extra_defs := global_setting_conf.get("extra_definitions"):
                        parsed_defs = [cst.parse_statement(inspect.getsource(obj)) for obj in extra_defs]
                        InsertAfterImportsVisitor.insert_after_imports(self.context, parsed_defs)

                    body.extend(self._get_statement_lines(setting, global_setting_conf))
                else:
                    value = getattr(self.django_context.settings, setting)
                    ann_str = TYPE_MAP.get(type(value), "Any")  # TODO, better way?
                    if ann_str == "Any":
                        self.add_typing_imports(["Any"])

                    body.append(
                        cst.SimpleStatementLine(
                            [
                                cst.AnnAssign(
                                    target=cst.Name(setting),
                                    annotation=cst.Annotation(helpers.parse_template_expression(ann_str)),
                                )
                            ]
                        )
                    )

        return updated_node.with_deep_changes(
            old_node=updated_node.body,
            body=body,
        )
