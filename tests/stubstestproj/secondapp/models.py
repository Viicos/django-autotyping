from django.db import models


class ModelTwo(models.Model):
    pass


class DuplicateModel(models.Model):
    """This model is also defined in `secondapp`, and is here to test _as imports_ in stubs."""
