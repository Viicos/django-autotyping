from typing_extensions import assert_type

from django.contrib.auth import authenticate, login, get_user_model, get_user, update_session_auth_hash
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.http.request import HttpRequest

from stubstestproj.accounts.models import User

req = HttpRequest()
abstract_user = AbstractBaseUser()

assert_type(authenticate(req), User | None)
assert_type(get_user_model(), type[User])
assert_type(get_user(req), User | AnonymousUser)

login(req, abstract_user)  # type: ignore
update_session_auth_hash(req, abstract_user)  # type: ignore
