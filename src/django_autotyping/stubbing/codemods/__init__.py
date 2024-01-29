from __future__ import annotations

from typing import Container, Literal

from django_autotyping._compat import TypeAlias

from .auth_functions_codemod import AuthFunctionsCodemod
from .base import StubVisitorBasedCodemod
from .call_command_codemod import CallCommandCodemod
from .create_overload_codemod import CreateOverloadCodemod
from .forward_relation_overload_codemod import ForwardRelationOverloadCodemod
from .get_model_overload_codemod import GetModelOverloadCodemod
from .query_lookups_overload_codemod import QueryLookupsOverloadCodemod
from .reverse_overload_codemod import ReverseOverloadCodemod
from .settings_codemod import SettingCodemod

__all__ = (
    "AuthFunctionsCodemod",
    "StubVisitorBasedCodemod",
    "CallCommandCodemod",
    "CreateOverloadCodemod",
    "ForwardRelationOverloadCodemod",
    "GetModelOverloadCodemod",
    "QueryLookupsOverloadCodemod",
    "ReverseOverloadCodemod",
    "SettingCodemod",
    "RulesT",
    "rules",
    "gather_codemods",
)

RulesT: TypeAlias = Literal["DJAS001", "DJAS002", "DJAS010", "DJAS011", "DJAS015", "DJAS016", "DJAS017"]

rules: list[tuple[RulesT, type[StubVisitorBasedCodemod]]] = [
    ("DJAS001", ForwardRelationOverloadCodemod),
    ("DJAS002", CreateOverloadCodemod),
    # ("DJAS003", QueryLookupsOverloadCodemod),
    ("DJAS010", GetModelOverloadCodemod),
    ("DJAS011", AuthFunctionsCodemod),
    ("DJAS015", ReverseOverloadCodemod),
    ("DJAS016", SettingCodemod),
    ("DJAS017", CallCommandCodemod),
]


def gather_codemods(
    ignore: Container[RulesT] = [], include: Container[RulesT] = ["DJAS017"]
) -> list[type[StubVisitorBasedCodemod]]:
    if include:
        return [rule[1] for rule in rules if rule[0] in include]
    return [rule[1] for rule in rules if rule[0] not in ignore]
