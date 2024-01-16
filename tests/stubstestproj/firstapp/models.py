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
