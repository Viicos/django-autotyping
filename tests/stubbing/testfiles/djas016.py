from typing_extensions import assert_type

from django.conf import settings

assert_type(settings.INSTALLED_APPS, list[str])
assert_type(settings.CUSTOM_SETTING, str)
