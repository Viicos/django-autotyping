from __future__ import annotations

from typing import Container, Literal

from django_autotyping._compat import TypeAlias

from .base import StubVisitorBasedCodemod
from .create_overload_codemod import CreateOverloadCodemod
from .forward_relation_overload_codemod import ForwardRelationOverloadCodemod
from .get_model_overload_codemod import GetModelOverloadCodemod
from .query_lookups_overload_codemod import QueryLookupsOverloadCodemod
from .reverse_overload_codemod import ReverseOverloadCodemod

__all__ = (
    "StubVisitorBasedCodemod",
    "CreateOverloadCodemod",
    "ForwardRelationOverloadCodemod",
    "GetModelOverloadCodemod",
    "QueryLookupsOverloadCodemod",
    "ReverseOverloadCodemod",
)

RulesT: TypeAlias = Literal["DJAS001", "DJAS002", "DJAS010", "DJAS011"]

rules: list[tuple[RulesT, type[StubVisitorBasedCodemod]]] = [
    ("DJAS001", ForwardRelationOverloadCodemod),
    ("DJAS002", CreateOverloadCodemod),
    # ("DJAS003", QueryLookupsOverloadCodemod),
    ("DJAS010", GetModelOverloadCodemod),
    ("DJAS011", ReverseOverloadCodemod),
]


def gather_codemods(
    ignore: Container[RulesT] = [], include: Container[RulesT] = []
) -> list[type[StubVisitorBasedCodemod]]:
    if include:
        return [rule[1] for rule in rules if rule[0] in include]
    return [rule[1] for rule in rules if rule[0] not in ignore]
