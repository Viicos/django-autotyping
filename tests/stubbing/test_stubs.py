from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path

import pytest
from mypy.api import run as run_mypy
from pyright import main as run_pyright

from django_autotyping.app_settings import StubsGenerationSettings
from django_autotyping.stubbing import create_local_django_stubs, run_codemods
from django_autotyping.stubbing.codemods import gather_codemods

TESTFILES = Path(__file__).parent / "testfiles"
STUBSTESTPROJ = Path(__file__).parents[1].joinpath("stubstestproj").absolute()

# fmt: off
testfiles_params = pytest.mark.parametrize(
    ["testfile", "rules", "stubs_settings"],
    [
        (TESTFILES / "djas001.py", ["DJAS001"], StubsGenerationSettings()),
        (TESTFILES / "djas001_no_plain_references.py", ["DJAS001"], StubsGenerationSettings(ALLOW_PLAIN_MODEL_REFERENCES=False)),  # noqa: E501
        (TESTFILES / "djas001_allow_non_set_type.py", ["DJAS001"], StubsGenerationSettings(ALLOW_NONE_SET_TYPE=True)),
    ],
)
# fmt: on


@pytest.fixture
def local_stubs(tmp_path) -> Path:
    create_local_django_stubs(tmp_path)
    return tmp_path


@pytest.mark.xfail(reason="mypy does not support setting the MYPYPATH without specifying a module or package to test.")
@pytest.mark.mypy
@testfiles_params
def test_mypy(
    monkeypatch,
    local_stubs,
    stubstestproj_context,
    # testfiles_params:
    testfile: Path,
    rules: list[str],
    stubs_settings: StubsGenerationSettings,
):
    stubs_settings = dataclasses.replace(stubs_settings, LOCAL_STUBS_DIR=local_stubs)

    codemods = gather_codemods(include=rules)
    run_codemods(codemods, stubstestproj_context, stubs_settings)

    # TODO this does not work for now: https://github.com/python/mypy/issues/16775
    monkeypatch.setenv("MYPYPATH", os.pathsep.join(map(str, [local_stubs.absolute(), STUBSTESTPROJ])))

    _, _, exit_code = run_mypy([str(testfile.absolute())])

    assert exit_code == 0


@pytest.mark.pyright
@testfiles_params
def test_pyright(
    tmp_path,
    local_stubs,
    stubstestproj_context,
    # testfiles_params:
    testfile: Path,
    rules: list[str],
    stubs_settings: StubsGenerationSettings,
):
    stubs_settings = dataclasses.replace(stubs_settings, LOCAL_STUBS_DIR=local_stubs)

    codemods = gather_codemods(include=rules)
    run_codemods(codemods, stubstestproj_context, stubs_settings)

    config_file = tmp_path / "pyrightconfig.json"
    config_file.write_text(
        json.dumps({"stubPath": str(local_stubs.absolute()), "extraPaths": [str(STUBSTESTPROJ.parent)]})
    )

    exit_code = run_pyright(["--project", str(config_file), str(testfile)])

    assert exit_code == 0
