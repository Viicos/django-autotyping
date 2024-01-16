from typing_extensions import assert_type

from django.db.models.expressions import Combinable
from django.db.models.fields.related_descriptors import ManyRelatedManager

from stubstestproj.firstapp.models import ModelOne, DuplicateModel as FirstAppDuplicateModel
from stubstestproj.secondapp.models import ModelTwo, DuplicateModel as SecondAppDuplicateModel

assert_type(ModelOne().model_two, ModelTwo)
assert_type(ModelOne().model_two_plain_reference, ModelTwo)
assert_type(ModelOne().model_two_nullable, ModelTwo | None)
assert_type(ModelOne().model_duplicate_firstapp, FirstAppDuplicateModel)
assert_type(ModelOne().model_duplicate_secondapp, SecondAppDuplicateModel)
assert_type(ModelOne().many_to_many_model_two, ManyRelatedManager[ModelTwo])

ModelOne().model_two = ModelTwo()
ModelOne().model_two = Combinable()
ModelOne().model_two_nullable = None
