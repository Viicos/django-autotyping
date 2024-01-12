from pathlib import Path

import pytest
from libcst.codemod import CodemodTest

from django_autotyping.app_settings import CodeGenerationSettings
from django_autotyping.codemodding.codemods import ForwardRelationTypingCodemod
from django_autotyping.codemodding.django_context import DjangoCodemodContext
from django_autotyping.codemodding.main import run_codemods

expected_no_type_checking_block = """
from django.db import models
from django.db.models import OneToOneField
from codemodtestproj.secondapp.models import ModelTwo


class ModelOne:
    a = models.ForeignKey("secondapp.ModelTwo", on_delete=models.CASCADE)


class ModelOne(object):
    a = models.ForeignKey("secondapp.ModelTwo", on_delete=models.CASCADE)


# Only this one should be transformed
class ModelOne(models.Model):
    a = models.ForeignKey["ModelTwo"]("secondapp.ModelTwo", on_delete=models.CASCADE)

    b = OneToOneField["ModelTwo"]("secondapp.ModelTwo", on_delete=models.CASCADE)

    c = models.ForeignKey["ModelOne"]("self", on_delete=models.CASCADE)
"""

expected_type_checking_block = """
from django.db import models
from django.db.models import OneToOneField
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codemodtestproj.secondapp.models import ModelTwo


class ModelOne:
    a = models.ForeignKey("secondapp.ModelTwo", on_delete=models.CASCADE)


class ModelOne(object):
    a = models.ForeignKey("secondapp.ModelTwo", on_delete=models.CASCADE)


# Only this one should be transformed
class ModelOne(models.Model):
    a = models.ForeignKey["ModelTwo"]("secondapp.ModelTwo", on_delete=models.CASCADE)

    b = OneToOneField["ModelTwo"]("secondapp.ModelTwo", on_delete=models.CASCADE)

    c = models.ForeignKey["ModelOne"]("self", on_delete=models.CASCADE)
"""


@pytest.mark.parametrize(
    ["type_checking_block", "expected"],
    [
        (True, expected_type_checking_block),
        (False, expected_no_type_checking_block),
    ],
)
def test_dja001(codemodtestproj_context: DjangoCodemodContext, type_checking_block: bool, expected: str):
    inpath = Path(__file__).parents[1] / "codemodtestproj" / "codemodtestproj" / "firstapp" / "models.py"

    code_generation_settings = CodeGenerationSettings(
        TYPE_CHECKING_BLOCK=type_checking_block,
        ASSUME_CLASS_GETITEM=True,
    )

    outcode = run_codemods(
        codemods=[ForwardRelationTypingCodemod],
        django_context=codemodtestproj_context,
        code_generation_settings=code_generation_settings,
        filename=str(inpath),
    )

    assert CodemodTest.make_fixture_data(expected) == CodemodTest.make_fixture_data(outcode)
