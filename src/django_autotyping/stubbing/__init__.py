from __future__ import annotations

import os
import shutil
import site
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
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
) -> dict[str, str]:
    """Given a list of codemods, apply them to the related files.

    Returns:
        A mapping between the stub file name and the new file content.
    """
    django_stubs_dir = stubs_settings.SOURCE_STUBS_DIR or _get_django_stubs_dir()

    # From 'codemod -> set[files]' to 'file -> list[codemods]'
    # (different codemods could apply to the same file(s))
    files_codemods_dct: defaultdict[str, list[type[StubsGenerationSettings]]] = defaultdict(list)
    for codemod in codemods:
        for stub_file in codemod.STUB_FILES:
            files_codemods_dct[stub_file].append(codemod)

    with ProcessPoolExecutor(min(len(files_codemods_dct), os.cpu_count() or 1)) as executor:
        futures = {
            executor.submit(
                _run_codemods_on_file, codemods, django_context, stubs_settings, django_stubs_dir / stub_file
            ): stub_file
            for stub_file, codemods in files_codemods_dct.items()
        }

        return {futures[future]: future.result() for future in as_completed(futures)}


def _run_codemods_on_file(
    codemods: list[type[StubVisitorBasedCodemod]],
    django_context: DjangoStubbingContext,
    stubs_settings: StubsGenerationSettings,
    source_file: Path,
) -> str:
    input_code = source_file.read_text(encoding="utf-8")
    input_module = cst.parse_module(input_code)

    for codemod in codemods:
        context = CodemodContext(
            filename=source_file.name, scratch={"django_context": django_context, "stubs_settings": stubs_settings}
        )
        transformer = codemod(context)

        input_module = transformer.transform_module(input_module)

    return input_module.code


def _get_django_stubs_dir() -> Path:
    # TODO should we use importlib.metadata.files instead?
    for dir in site.getsitepackages():
        if (path := Path(dir, "django-stubs")).is_dir():
            return path
    raise RuntimeError("Couldn't find 'django-stubs' in any of the site packages.")


def create_local_django_stubs(stubs_dir: Path, source_django_stubs: Path | None = None) -> None:
    """Copy the `django-stubs` package into the specified local stubs directory.

    If `source_django_stubs` is not provided, the first entry in site packages will be used.
    """
    source_django_stubs = source_django_stubs or _get_django_stubs_dir()
    if not (stubs_dir / "django-stubs").is_dir():
        shutil.copytree(source_django_stubs, stubs_dir / "django-stubs")

    # for stub_file in django_stubs_dir.glob("**/*.pyi"):
    #     # Make file relative to site packages, results in `Path("django-stubs/path/to/file.pyi")`
    #     relative_stub_file = stub_file.relative_to(django_stubs_dir.parent)
    #     symlinked_path = stubs_dir / relative_stub_file

    #     stub_file.mkdir()
