from typing import Literal

from typing_extensions import assert_type

from django.conf import settings

assert_type(settings.INSTALLED_APPS, list[str])
assert_type(settings.CUSTOM_SETTING, str)

# Special cased:
assert_type(settings.AUTH_USER_MODEL, Literal["accounts.User"])

# Added in Django 4.0, we currently test against 4.2:
assert_type(settings.SECURE_CROSS_ORIGIN_OPENER_POLICY, str | None)

# Deprecated since 4.2:
settings.STATICFILES_STORAGE  # type: ignore
