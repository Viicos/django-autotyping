from django.db import models


class ExtraModel(models.Model):
    # `ModelBase.__new__` registers every model to the default `Apps` class,
    # even if the model is not defined/exported in the `AppConfig`'s models module.
    # This can lead to cases where `AppConfig.models_module` is `None` because
    # no models module exists, however models are still registered under this
    # specific `AppConfig`.
    # See https://github.com/Viicos/django-autotyping/issues/59 as an example.
    pass
