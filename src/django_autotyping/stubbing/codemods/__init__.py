from __future__ import annotations

from typing import Container, Literal

from libcst.codemod import VisitorBasedCodemodCommand

from .create_overload_codemod import CreateOverloadCodemod
from .forward_relation_overload_codemod import ForwardRelationOverloadCodemod
from .query_lookups_overload_codemod import QueryLookupsOverloadCodemod

__all__ = (
    "CreateOverloadCodemod",
    "ForwardRelationOverloadCodemod",
    "QueryLookupsOverloadCodemod",
)

rules = [
    ("DJAS001", ForwardRelationOverloadCodemod),
    ("DJAS002", CreateOverloadCodemod),
    # ("DJAS003", QueryLookupsOverloadCodemod),
]

RulesT = Literal["DJAS001", "DJAS002"]


def gather_codemods(disabled: Container[RulesT]) -> list[type[VisitorBasedCodemodCommand]]:
    return [rule[1] for rule in rules if rule[0] not in disabled]
