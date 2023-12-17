from __future__ import annotations

from typing import Container, Literal

from libcst.codemod import VisitorBasedCodemodCommand

from .forward_relation_overload_codemod import ForwardRelationOverloadCodemod
from .query_lookups_overload_codemod import QueryLookupsOverloadCodemod

__all__ = ("ForwardRelationOverloadCodemod", "QueryLookupsOverloadCodemod")

rules = [
    ("DJAS001", ForwardRelationOverloadCodemod),
    # ("DJAS002", QueryLookupsOverloadCodemod),
]

RulesT = Literal["DJAS001"]


def gather_codemods(disabled: Container[RulesT]) -> list[type[VisitorBasedCodemodCommand]]:
    return [rule[1] for rule in rules if rule[0] not in disabled]
