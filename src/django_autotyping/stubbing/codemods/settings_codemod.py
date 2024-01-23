from __future__ import annotations

import inspect
import warnings

import libcst as cst
import libcst.matchers as m
from django import VERSION as DJANGO_VERSION
from libcst import helpers
from libcst.codemod.visitors import AddImportsVisitor

from django_autotyping._compat import NoneType

from ._global_settings_types import GLOBAL_SETTINGS, SettingTypingConfiguration
from ._utils import _indent
from .base import InsertAfterImportsVisitor, StubVisitorBasedCodemod

# Matchers:

CLASS_DEF_MATCHER = m.ClassDef(name=m.Name("LazySettings"))
"""Matches the `LazySettings` class definition."""

DEPRECATED_SETTING_NO_DOCSTRING = """
@property
@deprecated({message})
def {setting_name}(self) -> {type}: ...
""".strip()

DEPRECATED_SETTING_NO_DOCSTRING = """
@property
@deprecated({message})
def {setting_name}(self) -> {type}:
    {docstring}
""".strip()

TYPE_MAP = {
    int: "int",
    str: "str",
    NoneType: "Literal[None]",
}


class SettingCodemod(StubVisitorBasedCodemod):
    """A codemod that will add typing to the Django settings object.

    Depending on the Django version being used when running the stubs generation,
    the available settings might differ. The [`@deprecated`][warnings.deprecated]
    decorator will be used if necessary, thus making your type checker aware of
    the deprecation notice.

    Rule identifier: `DJAS016`.

    ```python
    from django.conf import settings

    reveal_type(settings.ADMINS)  # Revealed type is "list[tuple[str, str]]"
    reveal_type(settings.CUSTOM_SETTING)  # Revealed type is "str"
    reveal_type(settings.USE_DEPRECATED_PYTZ)  # Will be marked as deprecated by the type checker.
    ```

    !!! info "Experimental"
        Type hints might not reflect the actual type being used at runtime.
        For Django settings, all the possible types are taken into account (e.g. the
        `EMAIL_TIMEOUT` setting might be set to `10`, but as the default value is `None`,
        the reflected type hint will be `int | None`).

        For custom settings, only simple types are inferred. See
        [this issue](https://github.com/Viicos/django-autotyping/issues/40) for more details.
    """

    STUB_FILES = {"conf/__init__.pyi"}

    def _get_statement_lines(
        self, setting_name: str, setting_typing_conf: SettingTypingConfiguration
    ) -> list[cst.SimpleStatementLine]:
        docstring = setting_typing_conf.get("docs")

        if setting_typing_conf.get("deprecated_since", (float("inf"),)) <= DJANGO_VERSION:
            if not docstring:
                stmt = helpers.parse_template_statement(
                    DEPRECATED_SETTING_NO_DOCSTRING,
                    message=cst.SimpleString(f'"{setting_typing_conf.get("deprecated_message", "")}"'),
                    setting_name=cst.Name(setting_name),
                    type=cst.Annotation(cst.Name(setting_typing_conf["type"])),
                )
            else:
                _docstring = f'"""{_indent(docstring.strip(), indent_size=2)}"""'
                stmt = helpers.parse_template_statement(
                    DEPRECATED_SETTING_NO_DOCSTRING,
                    message=cst.SimpleString(f'"{setting_typing_conf.get("deprecated_message", "")}"'),
                    setting_name=cst.Name(setting_name),
                    type=cst.Annotation(cst.Name(setting_typing_conf["type"])),
                    docstring=cst.SimpleString(_docstring),
                )

            lines = [stmt]
            self.add_typing_imports(["deprecated"])

        else:
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
            if docstring:
                docstring = f'"""{_indent(docstring.strip())}"""'
                lines.append(cst.SimpleStatementLine([cst.Expr(cst.SimpleString(docstring))]))

        return lines

    @m.leave(CLASS_DEF_MATCHER)
    def mutate_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        body = list(updated_node.body.body)

        with warnings.catch_warnings():  # py3.11: `with warnings.catch_warnings(action="ignore")`
            warnings.simplefilter("ignore", category=DeprecationWarning)
            warnings.simplefilter("ignore", category=PendingDeprecationWarning)
            all_settings = {
                setting_name: getattr(self.django_context.settings, setting_name)
                for setting_name in dir(self.django_context.settings._wrapped)
                if setting_name != "SETTINGS_MODULE"
                if setting_name.isupper()
            }
        custom_settings = {k: v for k, v in all_settings.items() if k not in GLOBAL_SETTINGS}

        for setting_name, setting_typing_conf in GLOBAL_SETTINGS.items():
            if (
                setting_typing_conf.get("no_default")
                and setting_name not in all_settings
                or setting_typing_conf.get("added_in", (0,)) > DJANGO_VERSION
                or setting_typing_conf.get("removed_in", (float("inf"),)) <= DJANGO_VERSION
            ):
                continue

            if setting_name == "AUTH_USER_MODEL":
                setting_typing_conf = setting_typing_conf.copy()
                setting_typing_conf["type"] = f'Literal["{all_settings["AUTH_USER_MODEL"]}"]'

            if typing_imports := setting_typing_conf.get("typing_imports"):
                self.add_typing_imports(typing_imports)
            if extra_imports := setting_typing_conf.get("extra_imports"):
                imports = AddImportsVisitor._get_imports_from_context(self.context)
                imports.extend(extra_imports)
                self.context.scratch[AddImportsVisitor.CONTEXT_KEY] = imports
            if extra_defs := setting_typing_conf.get("extra_definitions"):
                parsed_defs = [cst.parse_statement(inspect.getsource(obj)) for obj in extra_defs]
                InsertAfterImportsVisitor.insert_after_imports(self.context, parsed_defs)

            body.extend(self._get_statement_lines(setting_name, setting_typing_conf))

        for setting_name, setting_value in custom_settings.items():
            ann_str = TYPE_MAP.get(type(setting_value), "Any")  # TODO, better way?
            if ann_str == "Any":
                self.add_typing_imports(["Any"])

            body.append(
                cst.SimpleStatementLine(
                    [
                        cst.AnnAssign(
                            target=cst.Name(setting_name),
                            annotation=cst.Annotation(helpers.parse_template_expression(ann_str)),
                        )
                    ]
                )
            )

        return updated_node.with_deep_changes(
            old_node=updated_node.body,
            body=body,
        )
