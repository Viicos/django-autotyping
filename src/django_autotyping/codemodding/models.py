from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from types import ModuleType
from typing import cast

from django.apps import AppConfig, apps
from django.db.models.fields.related import RelatedField

from ..typing import ModelType


@dataclass
class ForwardRelation:
    class_name: str
    nullable: bool
    has_class_getitem: bool
    model: ModelType

    @property
    def model_module(self) -> ModuleType:
        """The module object of the model linked to this relation."""
        return cast(ModuleType, inspect.getmodule(self.model))

    @property
    def app_config(self) -> AppConfig:
        """The `AppConfig` object where the model linked to this relation belongs."""
        return apps.get_app_config(self.model._meta.app_label)

    @property
    def app_models_module(self) -> ModuleType | None:
        """The module object where models of the app of the model linked to this relation are stored."""
        return self.app_config.models_module  # type: ignore[return-value]

    @classmethod
    def from_field(cls, field: RelatedField) -> ForwardRelation:
        return cls(
            class_name=field.__class__.__name__,
            nullable=field.null,
            has_class_getitem=hasattr(type(field), "__class_getitem__"),
            model=field.related_model,
        )


@dataclass
class ModelInfo:
    model: ModelType
    module: ModuleType
    forward_relations: dict[str, ForwardRelation] = field(default_factory=dict)

    @property
    def class_name(self) -> str:
        return self.model.__name__

    @property
    def filename(self) -> str:
        return cast(str, inspect.getsourcefile(self.model))

    @property
    def app_label(self) -> str:
        """The app label where the model belongs."""
        return self.model._meta.app_label

    @property
    def app_config(self) -> AppConfig:
        """The `AppConfig` object where the model belongs."""
        return self.model._meta.app_config

    @classmethod
    def from_model(cls, model: ModelType) -> ModelInfo:
        forward_relations = {
            field.name: ForwardRelation.from_field(field)
            for field in model._meta.get_fields()
            if isinstance(field, RelatedField)  # TODO isinstance check on `Field`?
            # if field.many_to_one  # TODO may be unnecessary?
        }

        return cls(
            model=model,
            module=inspect.getmodule(model),
            forward_relations=forward_relations,
        )
