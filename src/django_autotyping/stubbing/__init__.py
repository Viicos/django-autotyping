import shutil
import site
from pathlib import Path
from typing import Any

import libcst as cst
from django.apps import AppConfig
from django.apps.registry import Apps
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand

from ..app_settings import AUTOTYPING_DISABLED_RULES, AUTOTYPING_STUBS_DIR
from .codemods import gather_codemods


def post_migrate_receiver(sender: AppConfig, **kwargs: Any):
    apps: Apps = kwargs["apps"]
    codemods = gather_codemods(AUTOTYPING_DISABLED_RULES)

    # TODO depending on the future codemods, we might need to build
    # a specific Django context instead of passing apps.
    run_codemods(codemods, AUTOTYPING_STUBS_DIR, apps)


def run_codemods(codemods: list[type[VisitorBasedCodemodCommand]], stubs_dir: Path, apps: Apps) -> None:
    # Temp hack: the apps object from the post_migrate signal is a `StatesApp` instance, missing some data we need
    from django.apps import apps

    for codemod in codemods:
        context = CodemodContext(scratch={"django_models": apps.get_models()})

        transformer = codemod(context)

        for stub_file in codemod.STUB_FILES:  # TODO typechecking
            source_file = _get_django_stubs_dir() / stub_file
            target_file = stubs_dir / "django-stubs" / stub_file

            input_code = source_file.read_text(encoding="utf-8")
            input_module = cst.parse_module(input_code)
            output_module = transformer.transform_module(input_module)

            target_file.write_text(output_module.code, encoding="utf-8")


def _get_django_stubs_dir() -> Path:
    # TODO should we use importlib.metadata.files instead?
    for dir in site.getsitepackages():
        if (path := Path(dir, "django-stubs")).is_dir():
            return path


def create_stubs(stubs_dir: Path):
    stubs_dir.mkdir(exist_ok=True)
    django_stubs_dir = _get_django_stubs_dir()
    if not (stubs_dir / "django-stubs").is_dir():
        shutil.copytree(django_stubs_dir, stubs_dir / "django-stubs")

    # for stub_file in django_stubs_dir.glob("**/*.pyi"):
    #     # Make file relative to site packages, results in `Path("django-stubs/path/to/file.pyi")`
    #     relative_stub_file = stub_file.relative_to(django_stubs_dir.parent)
    #     symlinked_path = stubs_dir / relative_stub_file

    #     stub_file.mkdir()
