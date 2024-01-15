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
