from django.db import models


class ModelOne(models.Model):
    model_two = models.ForeignKey(
        "secondapp.ModelTwo",
        on_delete=models.CASCADE,
    )
    model_two_plain_reference = models.ForeignKey(
        "ModelTwo",
        on_delete=models.CASCADE,
    )
    model_two_nullable = models.ForeignKey(
        "secondapp.ModelTwo",
        on_delete=models.CASCADE,
        null=True,
    )
    model_duplicate_firstapp = models.ForeignKey(
        "firstapp.DuplicateModel",
        on_delete=models.CASCADE,
    )
    model_duplicate_secondapp = models.ForeignKey(
        "secondapp.DuplicateModel",
        on_delete=models.CASCADE,
    )

    many_to_many_model_two = models.ManyToManyField("secondapp.ModelTwo")


class DuplicateModel(models.Model):
    """This model is also defined in `secondapp`, and is here to test _as imports_ in stubs."""


class CharFieldsModel(models.Model):

    char_field = models.CharField()
    char_field_blank = models.CharField(blank=True)
    char_field_null = models.CharField(null=True)
    char_field_default = models.CharField(default="")

class DateFieldsModel(models.Model):

    date_field = models.DateField()
    date_field_auto_now = models.DateField(auto_now=True)
    date_field_auto_now_add = models.DateField(auto_now_add=True)

class AllFieldsModel(models.Model):

    integer_field = models.IntegerField()
    float_field = models.FloatField()
    decimal_field = models.DecimalField()
    text_field = models.TextField()
    boolean_field = models.BooleanField()
    ipadress_field = models.IPAddressField()
    datetime_field = models.DateTimeField()
    time_field = models.TimeField()
    uuid_field = models.UUIDField()

class ForeignKeyModel(models.Model):

    model_one = models.ForeignKey("firstapp.ModelOne", on_delete=models.CASCADE)
    model_one_null = models.ForeignKey("firstapp.ModelOne", on_delete=models.CASCADE, null=True)

class PrimaryKeyModel(models.Model):
    pk_field = models.CharField(primary_key=True)

class AltNameModel(models.Model):
    field = models.CharField(name="alt_name")
