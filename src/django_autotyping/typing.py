from __future__ import annotations

from typing import TYPE_CHECKING, Type

import libcst as cst
from django.db import models

ModelType = Type[models.Model]

if TYPE_CHECKING:
    # See https://github.com/Instagram/LibCST/issues/1075
    FlattenFunctionDef = cst.FlattenSentinel[cst.FunctionDef]
else:
    FlattenFunctionDef = cst.FunctionDef
