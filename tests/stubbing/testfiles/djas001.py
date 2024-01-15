from typing_extensions import assert_type

from django.db.models.expressions import Combinable

from stubstestproj.firstapp.models import ModelOne
from stubstestproj.secondapp.models import ModelTwo

assert_type(ModelOne().model_two, ModelTwo)
assert_type(ModelOne().model_two_plain_reference, ModelTwo)
assert_type(ModelOne().model_two_nullable, ModelTwo | None)

ModelOne().model_two = ModelTwo()
ModelOne().model_two = Combinable()
ModelOne().model_two_nullable = None
