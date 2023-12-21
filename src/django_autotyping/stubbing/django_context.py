import re

from django.apps.registry import Apps
from libcst.codemod.visitors import ImportItem

from django_autotyping.typing import ModelType


class DjangoStubbingContext:
    def __init__(self, apps: Apps):
        self.apps = apps

    @staticmethod
    def _get_model_alias(model: ModelType) -> str:
        """Return an alias of the model, by converting the app label to PascalCase and joining
        the app label to the model name.
        """
        app_label = model._meta.app_label.title()
        app_label = re.sub("([0-9A-Za-z])_(?=[0-9A-Z])", lambda m: m.group(1), app_label)
        return f"{app_label}{model.__name__}"

    @property
    def models(self) -> list[ModelType]:
        """All the defined models."""
        return self.apps.get_models()

    @property
    def model_imports(self) -> list[ImportItem]:
        """A list of `ImportItem` instances.

        Can be used to easily import all models in a stub file.
        """

        return [
            ImportItem(
                module_name=model._meta.app_config.models_module.__name__,
                obj_name=model.__name__,
                alias=self._get_model_alias(model) if self.is_duplicate(model) else None,
            )
            for model in self.models
        ]

    def is_duplicate(self, model: ModelType) -> bool:
        """Whether the model has a duplicate name with another model in a different app."""
        return len([m for m in self.models if m.__name__ == model.__name__]) >= 2  # noqa: PLR2004

    def get_model_name(self, model: ModelType) -> str:
        """Return the name of the model in the context of a stub file.

        If the model has a duplicate name, an alias is returned.
        """
        return self._get_model_alias(model) if self.is_duplicate(model) else model.__name__
