# Test with `MODEL_FIELDS_OPTIONAL=False`.

from datetime import date

from django.db.models.expressions import Combinable
from stubstestproj.firstapp.models import CharFieldsModel, DateFieldsModel, ForeignKeyModel, ModelOne, PrimaryKeyModel

CharFieldsModel()  # type: ignore
CharFieldsModel.objects.create()  # type: ignore
CharFieldsModel(char_field="")
CharFieldsModel.objects.create(char_field="")
CharFieldsModel(char_field=1)
CharFieldsModel.objects.create(char_field=1)
CharFieldsModel(char_field="", char_field_null=None)
CharFieldsModel.objects.create(char_field="", char_field_null=None)
CharFieldsModel(char_field=Combinable())
CharFieldsModel.objects.create(char_field=Combinable())

DateFieldsModel()  # type: ignore
DateFieldsModel.objects.create()  # type: ignore
DateFieldsModel(date_field=date.today())
DateFieldsModel.objects.create(date_field=date.today())

# We create an instance here and ignore the required fields:
model_one = ModelOne()  # type: ignore

ForeignKeyModel()  # type: ignore
ForeignKeyModel.objects.create()  # type: ignore
ForeignKeyModel(model_one=model_one)
ForeignKeyModel.objects.create(model_one=model_one)
ForeignKeyModel(model_one=model_one, model_one_null=model_one)
ForeignKeyModel.objects.create(model_one=model_one, model_one_null=model_one)
ForeignKeyModel(model_one=None)  # type: ignore
ForeignKeyModel.objects.create(model_one=None)  # type: ignore
ForeignKeyModel(model_one=model_one, model_one_null=None)
ForeignKeyModel.objects.create(model_one=model_one, model_one_null=None)

PrimaryKeyModel()
PrimaryKeyModel.objects.create()
