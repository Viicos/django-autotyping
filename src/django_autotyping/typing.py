from __future__ import annotations

from typing import Type

import libcst as cst
from django.db import models

ModelType = Type[models.Model]

FlattenFunctionDef = cst.FlattenSentinel[cst.FunctionDef]
