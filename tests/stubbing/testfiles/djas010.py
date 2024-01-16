from typing_extensions import assert_type

from django.apps import apps

from stubstestproj.firstapp.models import ModelOne

assert_type(apps.get_model("firstapp.ModelOne"), type[ModelOne])
assert_type(apps.get_model("firstapp", "ModelOne"), type[ModelOne])

apps.get_model("nonExisting")  # type: ignore
apps.get_model("nonExisting", "nonExisting")  # type: ignore
