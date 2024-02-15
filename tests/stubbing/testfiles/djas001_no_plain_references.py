from typing_extensions import assert_type

from stubstestproj.firstapp.models import ModelOne
from stubstestproj.secondapp.models import ModelTwo

assert_type(ModelOne().model_two, ModelTwo)
# At runtime, this is invalid:
assert_type(ModelOne().model_two_plain_reference, ModelTwo)  # type: ignore
