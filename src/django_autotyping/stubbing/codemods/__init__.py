from __future__ import annotations

from typing import Container, Literal

from libcst.codemod import VisitorBasedCodemodCommand

from .forward_relation_overload_codemod import ForwardRelationOverloadCodemod

__all__ = ("ForwardRelationOverloadCodemod",)

rules = [
    ("DJAS001", ForwardRelationOverloadCodemod),
]

RulesT = Literal["DJAS001"]


def gather_codemods(disabled: Container[RulesT]) -> list[type[VisitorBasedCodemodCommand]]:
    return [rule[1] for rule in rules if rule[0] not in disabled]
