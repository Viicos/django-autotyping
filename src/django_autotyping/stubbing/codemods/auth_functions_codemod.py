from __future__ import annotations

import libcst as cst
import libcst.matchers as m
from django.contrib.auth import get_user_model
from libcst import helpers
from libcst.codemod import CodemodContext
from libcst.codemod.visitors import AddImportsVisitor

from ._utils import get_param
from .base import StubVisitorBasedCodemod

# Matchers:

AUTHENTICATE_DEF_MATCHER = m.FunctionDef(name=m.Name("authenticate"))
"""Matches the `authenticate` function definition."""

LOGIN_DEF_MATCHER = m.FunctionDef(name=m.Name("login"))
"""Matches the `login` function definition."""

GET_USER_MODEL_DEF_MATCHER = m.FunctionDef(name=m.Name("get_user_model"))
"""Matches the `get_user_model` function definition."""

GET_USER_DEF_MATCHER = m.FunctionDef(name=m.Name("get_user"))
"""Matches the `get_user` function definition."""

UPDATE_SESSION_AUTH_HASH_DEF_MATCHER = m.FunctionDef(name=m.Name("update_session_auth_hash"))
"""Matches the `update_session_auth_hash` function definition."""


class AuthFunctionsCodemod(StubVisitorBasedCodemod):
    """A codemod that will add a custom return type to the to auth related functions.

    The following functions are affected:

    - [`authenticate`][django.contrib.auth.authenticate]
    - [`login`][django.contrib.auth.login]
    - [`get_user_model`][django.contrib.auth.get_user_model]
    - [`get_user`][django.contrib.auth.get_user]
    - [`update_session_auth_hash`][django.contrib.auth.update_session_auth_hash]

    Rule identifier: `DJAS011`.

    ```python
    from django.contrib.auth import authenticate, get_user_model, get_user

    reveal_type(authenticate(rq, **creds))  # Revealed type is "YourCustomUser | None"
    reveal_type(get_user_model())  # Revealed type is "type[YourCustomUser]"
    reveal_type(get_user(rq))  # Revealed type is "YourCustomUser | AnonymousUser"
    ```
    """

    STUB_FILES = {"contrib/auth/__init__.pyi"}

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        user_model = get_user_model()
        self.user_model_name = user_model.__name__

        AddImportsVisitor.add_needed_import(
            self.context,
            module=user_model._meta.app_config.models_module.__name__,
            obj=self.user_model_name,
        )

    @m.leave(AUTHENTICATE_DEF_MATCHER)
    def mutate_AuthenticateFunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        return updated_node.with_changes(
            returns=cst.Annotation(helpers.parse_template_expression(f"{self.user_model_name} | None"))
        )

    @m.leave(LOGIN_DEF_MATCHER)
    def mutate_LoginFunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        user_param = get_param(updated_node, "user")
        return updated_node.with_deep_changes(
            user_param, annotation=cst.Annotation(helpers.parse_template_expression(f"{self.user_model_name} | None"))
        )

    @m.leave(GET_USER_DEF_MATCHER)
    def mutate_GetUserFunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        return updated_node.with_changes(
            returns=cst.Annotation(helpers.parse_template_expression(f"{self.user_model_name} | AnonymousUser"))
        )

    @m.leave(GET_USER_MODEL_DEF_MATCHER)
    def mutate_GetUserModelFunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        return updated_node.with_changes(
            returns=cst.Annotation(helpers.parse_template_expression(f"type[{self.user_model_name}]"))
        )

    @m.leave(UPDATE_SESSION_AUTH_HASH_DEF_MATCHER)
    def mutate_UpdateSessionAuthHashFunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        user_param = get_param(updated_node, "user")
        return updated_node.with_deep_changes(
            user_param, annotation=cst.Annotation(helpers.parse_template_expression(self.user_model_name))
        )
