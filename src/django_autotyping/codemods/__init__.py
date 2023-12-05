from __future__ import annotations

from typing import Literal

from libcst.codemod import VisitorBasedCodemodCommand

from .forward_relation_typing_visitor import ForwardRelationTypingVisitor

__all__ = ("ForwardRelationTypingVisitor", "rules", "gather_codemods")

rules = [
    ("DJA001", ForwardRelationTypingVisitor),
]

RulesT = Literal["DJA001"]


def gather_codemods(disabled: list[str]) -> list[type[VisitorBasedCodemodCommand]]:
    return [rule[1] for rule in rules if rule[0] not in disabled]
