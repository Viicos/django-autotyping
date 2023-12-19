import shutil
import site
from pathlib import Path
from typing import Any

import libcst as cst
from django.apps import AppConfig
from django.apps.registry import Apps
from django.conf import settings
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand

from .codemods import gather_codemods
from .django_context import DjangoStubbingContext
from .settings import StubSettings


def post_migrate_receiver(sender: AppConfig, **kwargs: Any):
    stub_settings = StubSettings.from_django_settings(settings)

    create_stubs(stub_settings.stubs_dir)

    codemods = gather_codemods(stub_settings.disabled_rules)

    apps: Apps = kwargs["apps"]
    # Temp hack: the apps object from the post_migrate signal is a `StatesApp` instance, missing some data we need
    from django.apps import apps

    django_context = DjangoStubbingContext(apps)

    run_codemods(codemods, django_context, stub_settings)


def run_codemods(
    codemods: list[type[VisitorBasedCodemodCommand]],
    django_context: DjangoStubbingContext,
    stub_settings: StubSettings,
) -> None:
    for codemod in codemods:
        context = CodemodContext(scratch={"django_context": django_context, "stub_settings": stub_settings})

        transformer = codemod(context)

        for stub_file in codemod.STUB_FILES:  # TODO typechecking
            source_file = _get_django_stubs_dir() / stub_file  # TODO should be an argument to this func
            target_file = stub_settings.stubs_dir / "django-stubs" / stub_file

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
