from __future__ import annotations

from typing import Container, Literal

from django_autotyping._compat import TypeAlias

from .auth_functions_codemod import AuthFunctionsCodemod
from .base import StubVisitorBasedCodemod
from .call_command_codemod import CallCommandCodemod
from .create_overload_codemod import CreateOverloadCodemod
from .forward_relation_overload_codemod import ForwardRelationOverloadCodemod
from .get_model_overload_codemod import GetModelOverloadCodemod
from .model_init_overload_codemod import ModelInitOverloadCodemod
from .query_lookups_overload_codemod import QueryLookupsOverloadCodemod
from .reverse_overload_codemod import ReverseOverloadCodemod
from .settings_codemod import SettingCodemod
from .template_loading_codemod import TemplateLoadingCodemod

__all__ = (
    "AuthFunctionsCodemod",
    "CallCommandCodemod",
    "CreateOverloadCodemod",
    "ForwardRelationOverloadCodemod",
    "GetModelOverloadCodemod",
    "QueryLookupsOverloadCodemod",
    "ReverseOverloadCodemod",
    "RulesT",
    "SettingCodemod",
    "StubVisitorBasedCodemod",
    "TemplateLoadingCodemod",
    "gather_codemods",
    "rules",
)

RulesT: TypeAlias = Literal["DJAS001", "DJAS002", "DJAS003", "DJAS010", "DJAS011", "DJAS015", "DJAS016", "DJAS017"]

rules: list[tuple[RulesT, type[StubVisitorBasedCodemod]]] = [
    ("DJAS001", ForwardRelationOverloadCodemod),
    ("DJAS002", CreateOverloadCodemod),
    ("DJAS003", ModelInitOverloadCodemod),
    # ("DJAS004", QueryLookupsOverloadCodemod),
    ("DJAS010", GetModelOverloadCodemod),
    ("DJAS011", AuthFunctionsCodemod),
    ("DJAS015", ReverseOverloadCodemod),
    ("DJAS016", SettingCodemod),
    ("DJAS017", TemplateLoadingCodemod),
    # ("DJAS017", CallCommandCodemod),
]


def gather_codemods(
    ignore: Container[RulesT] = [], include: Container[RulesT] = []
) -> list[type[StubVisitorBasedCodemod]]:
    if include:
        return [rule[1] for rule in rules if rule[0] in include]
    return [rule[1] for rule in rules if rule[0] not in ignore]
