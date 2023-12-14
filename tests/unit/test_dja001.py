from pathlib import Path

import pytest
from libcst.codemod import CodemodTest

from django_autotyping.codemodding.codemods import ForwardRelationTypingCodemod
from django_autotyping.codemodding.django_utils import DjangoContext
from django_autotyping.codemodding.main import run_codemods

expected_no_type_checking_block = """
from django.db import models
from django.db.models import OneToOneField
from sampleproject.secondapp.models import ModelTwo


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
    from sampleproject.secondapp.models import ModelTwo


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
def test_dja001(sampleproject_context: DjangoContext, type_checking_block: bool, expected):
    sampleproject_context.assume_class_getitem = True

    inpath = Path(__file__).parents[1] / "sampleproject" / "sampleproject" / "firstapp" / "models.py"

    outcode = run_codemods(
        codemods=[ForwardRelationTypingCodemod],
        django_context=sampleproject_context,
        filename=str(inpath),
        type_checking_block=type_checking_block,
    )

    assert CodemodTest.make_fixture_data(expected) == CodemodTest.make_fixture_data(outcode)
