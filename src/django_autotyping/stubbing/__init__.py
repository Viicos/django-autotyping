import shutil
import site
from pathlib import Path

import libcst as cst
from libcst.codemod import CodemodContext

from django_autotyping.app_settings import StubsGenerationSettings

from .codemods import StubVisitorBasedCodemod
from .django_context import DjangoStubbingContext


def run_codemods(
    codemods: list[type[StubVisitorBasedCodemod]],
    django_context: DjangoStubbingContext,
    stubs_settings: StubsGenerationSettings,
) -> None:
    for codemod in codemods:
        for stub_file in codemod.STUB_FILES:
            context = CodemodContext(
                filename=stub_file, scratch={"django_context": django_context, "stub_settings": stubs_settings}
            )
            transformer = codemod(context)
            source_file = _get_django_stubs_dir() / stub_file  # TODO should be an argument to this func
            target_file = stubs_settings.stubs_dir / "django-stubs" / stub_file

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
