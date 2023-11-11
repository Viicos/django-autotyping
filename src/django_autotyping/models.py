import inspect
from dataclasses import dataclass, field

from django.db.models.fields.related import RelatedField

from .typing import ModelType


@dataclass
class ForwardRelation:
    class_name: str
    nullable: bool

    @classmethod
    def from_field(cls, field: RelatedField) -> "ForwardRelation":
        return cls(
            class_name=field.__class__.__name__,
            nullable=field.null,
        )


@dataclass
class ModelInfo:
    filename: str
    class_name: str

    forward_relations: dict[str, ForwardRelation] = field(default_factory=dict)

    @classmethod
    def from_model(cls, model: ModelType) -> "ModelInfo":
        forward_relations = {
            field.name: ForwardRelation.from_field(field)
            for field in model._meta.get_fields()
            if isinstance(field, RelatedField)  # TODO isinstance check on `Field`?
            if field.many_to_one
        }

        return cls(
            filename=inspect.getsourcefile(model),
            class_name=model.__name__,
            forward_relations=forward_relations,
        )
