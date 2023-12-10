from __future__ import annotations

from typing import Container, Literal

from libcst.codemod import VisitorBasedCodemodCommand

from .forward_relation_typing_codemod import ForwardRelationTypingCodemod

__all__ = ("ForwardRelationTypingCodemod", "rules", "gather_codemods")

rules = [
    ("DJA001", ForwardRelationTypingCodemod),
]

RulesT = Literal["DJA001"]


def gather_codemods(disabled: Container[RulesT]) -> list[type[VisitorBasedCodemodCommand]]:
    return [rule[1] for rule in rules if rule[0] not in disabled]
