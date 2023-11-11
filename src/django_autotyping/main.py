from __future__ import annotations

from pathlib import Path

import libcst as cst
from libcst.codemod import CodemodContext
from libcst.metadata import FullRepoManager, FullyQualifiedNameProvider

from .codemods import AnyToOneTypingVisitor
from .django_utils import ModelInfo


def main(model_infos: list[ModelInfo]) -> None:
    model_filenames = set(model_info.filename for model_info in model_infos)
    filenames = [str(path.relative_to(".")) for path in model_filenames]

    manager = FullRepoManager(".", filenames, {FullyQualifiedNameProvider})
    manager.resolve_cache()

    for filename in filenames:
        code = Path(filename).read_text(encoding="utf-8")
        module = cst.parse_module(code)

        context = CodemodContext(
            metadata_manager=manager,
            filename=filename,
            scratch={},
        )
        filename_models = [model for model in model_infos if Path(model.filename) == Path(filename)]

        visitor = AnyToOneTypingVisitor(
            context=context,
            model_infos=filename_models,
        )

        visitor.transform_module(module)
