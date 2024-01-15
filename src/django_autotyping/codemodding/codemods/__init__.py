from __future__ import annotations

__all__ = ("ForwardRelationTypingCodemod", "RulesT", "rules", "gather_codemods")

from typing import Container, Literal

from django_autotyping._compat import TypeAlias

from .base import BaseVisitorBasedCodemod
from .forward_relation_typing_codemod import ForwardRelationTypingCodemod

RulesT: TypeAlias = Literal["DJA001"]

rules: list[tuple[RulesT, type[BaseVisitorBasedCodemod]]] = [
    ("DJA001", ForwardRelationTypingCodemod),
]


def gather_codemods(
    ignore: Container[RulesT] = [], include: Container[RulesT] = []
) -> list[type[BaseVisitorBasedCodemod]]:
    if include:
        return [rule[1] for rule in rules if rule[0] in include]
    return [rule[1] for rule in rules if rule[0] not in ignore]
