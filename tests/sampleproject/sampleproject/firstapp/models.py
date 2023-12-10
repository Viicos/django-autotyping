from django.db import models
from django.db.models import OneToOneField


class ModelOne:
    a = models.ForeignKey("secondapp.ModelTwo", on_delete=models.CASCADE)

    b = OneToOneField("secondapp.ModelTwo", on_delete=models.CASCADE)


class ModelOne(object):
    a = models.ForeignKey("secondapp.ModelTwo", on_delete=models.CASCADE)

    b = OneToOneField("secondapp.ModelTwo", on_delete=models.CASCADE)


# Only this one should be transformed
class ModelOne(models.Model):
    a = models.ForeignKey("secondapp.ModelTwo", on_delete=models.CASCADE)

    b = OneToOneField("secondapp.ModelTwo", on_delete=models.CASCADE)
