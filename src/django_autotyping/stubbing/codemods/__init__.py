from __future__ import annotations

from typing import Container, Literal

from libcst.codemod import VisitorBasedCodemodCommand

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

rules = [
    ("DJAS001", ForwardRelationOverloadCodemod),
    ("DJAS002", CreateOverloadCodemod),
    # ("DJAS003", QueryLookupsOverloadCodemod),
    ("DJAS010", GetModelOverloadCodemod),
    ("DJAS011", ReverseOverloadCodemod),
]

RulesT = Literal["DJAS001", "DJAS002", "DJAS010", "DJAS011"]


def gather_codemods(disabled: Container[RulesT]) -> list[type[VisitorBasedCodemodCommand]]:
    return [rule[1] for rule in rules if rule[0] not in disabled]
