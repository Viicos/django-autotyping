from typing_extensions import assert_type

from stubstestproj.firstapp.models import ModelOne
from stubstestproj.secondapp.models import ModelTwo

assert_type(ModelOne().model_two, ModelTwo)

ModelOne().model_two = None
