# Test with `MODEL_FIELDS_OPTIONAL=True` (the default).

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from django.db.models.expressions import Combinable
from stubstestproj.firstapp.models import (
    AllFieldsModel,
    AltNameModel,
    CharFieldsModel,
    DateFieldsModel,
    DateTimeFieldsModel,
    ForeignKeyModel,
    ModelOne,
)

CharFieldsModel()
CharFieldsModel.objects.create()
CharFieldsModel(char_field="")
CharFieldsModel.objects.create(char_field="")
CharFieldsModel(char_field=1)
CharFieldsModel.objects.create(char_field=1)
CharFieldsModel(char_field_null=None)
CharFieldsModel.objects.create(char_field_null=None)
CharFieldsModel(char_field=Combinable())
CharFieldsModel.objects.create(char_field=Combinable())

DateFieldsModel(date_field="")
DateFieldsModel.objects.create(date_field="")
DateFieldsModel(date_field=date.today())
DateFieldsModel.objects.create(date_field=date.today())

DateTimeFieldsModel(datetime_field="")
DateTimeFieldsModel.objects.create(datetime_field="")
DateTimeFieldsModel(datetime_field=datetime.now())
DateTimeFieldsModel.objects.create(datetime_field=datetime.now())
DateTimeFieldsModel(datetime_field=date.today())
DateTimeFieldsModel.objects.create(datetime_field=date.today())

AllFieldsModel(integer_field=1)
AllFieldsModel.objects.create(integer_field=1)
AllFieldsModel(integer_field=1.0)
AllFieldsModel.objects.create(integer_field=1.0)
AllFieldsModel(integer_field="1")
AllFieldsModel.objects.create(integer_field="1")

AllFieldsModel(float_field=1)
AllFieldsModel.objects.create(float_field=1)
AllFieldsModel(float_field=1.0)
AllFieldsModel.objects.create(float_field=1.0)
AllFieldsModel(float_field="1")
AllFieldsModel.objects.create(float_field="1")

AllFieldsModel(decimal_field=Decimal(1))
AllFieldsModel.objects.create(decimal_field=Decimal(1))
AllFieldsModel(decimal_field=1)
AllFieldsModel.objects.create(decimal_field=1)
AllFieldsModel(decimal_field=1.0)
AllFieldsModel.objects.create(decimal_field=1.0)
AllFieldsModel(decimal_field="1")
AllFieldsModel.objects.create(decimal_field="1")

AllFieldsModel(text_field="")
AllFieldsModel.objects.create(text_field="")
# TODO why is this different from char_field?
AllFieldsModel(text_field=1)  # type: ignore
AllFieldsModel.objects.create(text_field=1)  # type: ignore

AllFieldsModel(boolean_field=False)
AllFieldsModel.objects.create(boolean_field=False)
AllFieldsModel(boolean_field=True)
AllFieldsModel.objects.create(boolean_field=True)
AllFieldsModel(boolean_field=False)
AllFieldsModel.objects.create(boolean_field=False)

AllFieldsModel(ipadress_field="")
AllFieldsModel.objects.create(ipadress_field="")

AllFieldsModel(datetime_field="")
AllFieldsModel.objects.create(datetime_field="")
AllFieldsModel(datetime_field=datetime.now())
AllFieldsModel.objects.create(datetime_field=datetime.now())
AllFieldsModel(datetime_field=date.today())
AllFieldsModel.objects.create(datetime_field=date.today())

AllFieldsModel(time_field="")
AllFieldsModel.objects.create(time_field="")
AllFieldsModel(time_field=datetime.now())
AllFieldsModel.objects.create(time_field=datetime.now())
AllFieldsModel(time_field=time())
AllFieldsModel.objects.create(time_field=time())

AllFieldsModel(uuid_field="")
AllFieldsModel.objects.create(uuid_field="")
AllFieldsModel(uuid_field=UUID())
AllFieldsModel.objects.create(uuid_field=UUID())

ForeignKeyModel(model_one=ModelOne())
ForeignKeyModel.objects.create(model_one=ModelOne())
ForeignKeyModel(model_one_null=ModelOne())
ForeignKeyModel.objects.create(model_one_null=ModelOne())
ForeignKeyModel(model_one=None)  # type: ignore
ForeignKeyModel.objects.create(model_one=None)  # type: ignore
ForeignKeyModel(model_one_null=None)
ForeignKeyModel.objects.create(model_one_null=None)

AltNameModel(field="")  # type: ignore
AltNameModel(alt_name="")
