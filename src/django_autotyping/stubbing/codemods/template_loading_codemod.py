from __future__ import annotations

import libcst as cst
import libcst.matchers as m
from libcst.codemod import CodemodContext

from django_autotyping.typing import FlattenFunctionDef

from ._utils import get_kw_param, get_param, to_pascal
from .base import InsertAfterImportsVisitor, StubVisitorBasedCodemod
from .constants import OVERLOAD_DECORATOR


class _All:
    pass


ALL = _All()
"""Sentinel value to indicate an overload should include all template names."""

# Matchers:

GET_TEMPLATE_DEF_MATCHER = m.FunctionDef(name=m.Name("get_template"))
"""Matches the `get_template` function definition."""

SELECT_TEMPLATE_DEF_MATCHER = m.FunctionDef(name=m.Name("select_template"))
"""Matches the `select_template` function definition."""

RENDER_TO_STRING_DEF_MATCHER = m.FunctionDef(name=m.Name("render_to_string"))
"""Matches the `render_to_string` function definition."""


class TemplateLoadingCodemod(StubVisitorBasedCodemod):
    """A codemod that will add overloads for template loading functions:

    - [`get_template`][django.template.loader.get_template]
    - [`select_template`][django.template.loader.select_template]
    - [`render_to_string`][django.template.loader.render_to_string]

    Rule identifier: `DJAS017`.

    ```python
    from django.template.loader import get_template

    get_template("a_template.html")  # 'a_template.html' can be from any engine
    get_template("a_django_template.html", using="django")
    get_template("not_a_jinja2_template.html", using="my_jinja2_engine")  # Type error
    ```

    !!! warning "Limited support"
        Engines other that Django and custom loaders are not supported yet.
    """

    STUB_FILES = {"template/loader.pyi"}

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.add_typing_imports(["Literal", "TypeAlias", "overload"])
        self.engines_literal_names = self.get_engines_literal_names()

    def get_engines_literal_names(self) -> dict[str | _All, str]:
        engines_info = self.django_context.template_engines_info

        engines_literal_names: dict[str | _All, str] = {}

        for engine_name, engine_info in engines_info.items():
            literal_name = f"{to_pascal(engine_name)}Templates"
            literals = ", ".join(f'"{name}"' for name in engine_info["template_names"])

            InsertAfterImportsVisitor.insert_after_imports(
                self.context, [cst.parse_statement(f"{literal_name}: TypeAlias = Literal[{literals}]")]
            )

            engines_literal_names[engine_name] = literal_name

        if len(engines_info) >= 2:  # noqa: PLR2004
            all_names: set[str] = set()
            for engine_info in reversed(engines_info.values()):
                all_names.update(engine_info["template_names"])

            # Ideally `AllTemplates` but 'all' might be an engine name already
            literal_name = "TemplatesAll"

            literals = ", ".join(f'"{name}"' for name in all_names)

            InsertAfterImportsVisitor.insert_after_imports(
                self.context, [cst.parse_statement(f"{literal_name}: TypeAlias = Literal[{literals}]")]
            )

            engines_literal_names[ALL] = literal_name

        return engines_literal_names

    @m.leave(GET_TEMPLATE_DEF_MATCHER | SELECT_TEMPLATE_DEF_MATCHER | RENDER_TO_STRING_DEF_MATCHER)
    def mutate_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> FlattenFunctionDef:
        is_render_to_string = updated_node.name.value == "render_to_string"
        is_select_template = updated_node.name.value == "select_template"
        template_name_arg = "template_name_list" if is_select_template else "template_name"

        if len(self.engines_literal_names) == 1:
            # One engine: no overloads needed.
            engine_name, literal_name = next(iter(self.engines_literal_names.items()))

            new_node = updated_node.with_deep_changes(
                old_node=get_param(updated_node, "using"),
                annotation=cst.Annotation(cst.parse_expression(f'Literal["{engine_name}"] | None')),
            )

            annotation = cst.parse_expression(f"list[{literal_name}]") if is_select_template else cst.Name(literal_name)

            new_node = new_node.with_deep_changes(
                old_node=get_param(new_node, template_name_arg), annotation=cst.Annotation(annotation)
            )

            return new_node

        overload = updated_node.with_changes(decorators=[OVERLOAD_DECORATOR])
        overloads: list[cst.FunctionDef] = []

        for engine_name, literal_name in self.engines_literal_names.items():
            annotation = cst.parse_expression(f"list[{literal_name}]") if is_select_template else cst.Name(literal_name)

            overload_ = overload.with_deep_changes(
                old_node=get_param(overload, template_name_arg), annotation=cst.Annotation(annotation)
            )

            if engine_name is ALL:
                overload_ = overload_.with_deep_changes(
                    old_node=get_param(overload_, "using"),
                    annotation=cst.Annotation(cst.Name("None")),
                )
            else:
                get_param_func = get_param
                if is_render_to_string:
                    # Make all params following 'template_name' kw-only:
                    overload_ = overload_.with_deep_changes(
                        old_node=overload_.params,
                        star_arg=cst.ParamStar(),
                        params=[get_param(overload_, "template_name")],
                        kwonly_params=[p for p in overload_.params.params if p.name.value != "template_name"],
                    )
                    get_param_func = get_kw_param

                overload_ = overload_.with_deep_changes(
                    old_node=get_param_func(overload_, "using"),
                    annotation=cst.Annotation(cst.parse_expression(f'Literal["{engine_name}"]')),
                    default=None,
                    equal=cst.MaybeSentinel.DEFAULT,
                )

            overloads.append(overload_)

        return cst.FlattenSentinel(overloads)
