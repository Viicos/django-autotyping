from __future__ import annotations

from pathlib import Path
from typing import Callable, TypedDict

from django.template.backends.base import BaseEngine
from django.template.backends.django import DjangoTemplates

try:
    from django.template.backends.jinja2 import Jinja2

    has_jinja2 = True
except ImportError:
    has_jinja2 = False


class EngineInfo(TypedDict):
    backend_class: str
    template_names: list[str]


def _get_django_template_names(engine: DjangoTemplates) -> list[str]:
    # would benefit from an ordered set
    ordered_template_names: dict[str, None] = {}

    for dir in engine.template_dirs:
        ordered_template_names.update(
            {str(k.relative_to(dir)): None for k in filter(lambda p: p.is_file(), Path(dir).rglob("*"))}
        )

    return list(ordered_template_names)


if has_jinja2:

    def _get_jinja2_template_names(engine: Jinja2) -> list[str]:
        # TODO Make use of `BaseLoader.list_templates()`
        return []


ENGINE_HANDLERS: dict[type[BaseEngine], Callable[[BaseEngine], list[str]]] = {
    DjangoTemplates: _get_django_template_names,
}

if has_jinja2:
    ENGINE_HANDLERS[Jinja2] = _get_jinja2_template_names


def get_template_names(engine: BaseEngine) -> list[str]:
    if type(engine) not in ENGINE_HANDLERS:
        return []
    return ENGINE_HANDLERS[type(engine)](engine)
